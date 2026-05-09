"""Knowledge-graph API routes — project-scoped, server-side persistent state."""

import os
import traceback
import threading
from flask import request, jsonify

from . import graph_bp
from ..config import Config
from ..extensions import limiter
from ..services.ontology_generator import OntologyGenerator
from ..services.graph_builder import GraphBuilderService
from ..services.text_processor import TextProcessor
from ..utils.file_parser import FileParser
from ..utils.logger import get_logger
from ..models.task import TaskManager, TaskStatus
from ..models.project import ProjectManager, ProjectStatus

logger = get_logger('mirofish.api')


def allowed_file(filename: str) -> bool:
    """Return True if the filename has an allowed extension."""
    if not filename or '.' not in filename:
        return False
    ext = os.path.splitext(filename)[1].lower().lstrip('.')
    return ext in Config.ALLOWED_EXTENSIONS


# ── Project management ────────────────────────────────────────────────────────

@graph_bp.route('/project/<project_id>', methods=['GET'])
def get_project(project_id: str):
    """Return project details by ID."""
    project = ProjectManager.get_project(project_id)
    
    if not project:
        return jsonify({
            "success": False,
            "error": f"Project not found: {project_id}"
        }), 404
    
    return jsonify({
        "success": True,
        "data": project.to_dict()
    })


@graph_bp.route('/project/list', methods=['GET'])
def list_projects():
    """List all projects (most recent first)."""
    limit = request.args.get('limit', 50, type=int)
    projects = ProjectManager.list_projects(limit=limit)
    
    return jsonify({
        "success": True,
        "data": [p.to_dict() for p in projects],
        "count": len(projects)
    })


@graph_bp.route('/project/<project_id>', methods=['DELETE'])
def delete_project(project_id: str):
    """Delete a project and its files."""
    success = ProjectManager.delete_project(project_id)
    
    if not success:
        return jsonify({
            "success": False,
            "error": f"Project not found or delete failed: {project_id}"
        }), 404

    return jsonify({
        "success": True,
        "message": f"Project deleted: {project_id}"
    })


@graph_bp.route('/project/<project_id>/reset', methods=['POST'])
def reset_project(project_id: str):
    """Reset a project back to ontology-generated status so the graph can be rebuilt."""
    project = ProjectManager.get_project(project_id)

    if not project:
        return jsonify({
            "success": False,
            "error": f"Project not found: {project_id}"
        }), 404

    if project.ontology:
        project.status = ProjectStatus.ONTOLOGY_GENERATED
    else:
        project.status = ProjectStatus.CREATED
    
    project.graph_id = None
    project.graph_build_task_id = None
    project.error = None
    ProjectManager.save_project(project)
    
    return jsonify({
        "success": True,
        "message": f"Project reset: {project_id}",
        "data": project.to_dict()
    })


# ── Ontology generation ───────────────────────────────────────────────────────

@graph_bp.route('/ontology/generate', methods=['POST'])
@limiter.limit("10 per hour")
def generate_ontology():
    """
    Upload product documents and generate a Zep ontology definition.

    Multipart form fields:
      files                  — one or more PDF / MD / TXT files
      simulation_requirement — (required) description of the simulation goal
      project_name           — (optional) human-readable project name
      additional_context     — (optional) extra instructions for the LLM

    Returns:
      { "success": true, "data": { "project_id", "ontology", "files", ... } }
    """
    try:
        logger.info("Generating ontology")

        simulation_requirement = request.form.get('simulation_requirement', '')
        project_name = request.form.get('project_name', 'Unnamed Project')
        additional_context = request.form.get('additional_context', '')

        if not simulation_requirement:
            return jsonify({"success": False, "error": "simulation_requirement is required"}), 400

        uploaded_files = request.files.getlist('files')
        if not uploaded_files or all(not f.filename for f in uploaded_files):
            return jsonify({"success": False, "error": "Upload at least one document"}), 400

        project = ProjectManager.create_project(name=project_name)
        project.simulation_requirement = simulation_requirement
        logger.info("Created project: %s", project.project_id)

        document_texts = []
        all_text = ""

        for file in uploaded_files:
            if file and file.filename and allowed_file(file.filename):
                file_info = ProjectManager.save_file_to_project(
                    project.project_id, file, file.filename
                )
                project.files.append({
                    "filename": file_info["original_filename"],
                    "size": file_info["size"]
                })
                text = FileParser.extract_text(file_info["path"])
                text = TextProcessor.preprocess_text(text)
                document_texts.append(text)
                all_text += f"\n\n=== {file_info['original_filename']} ===\n{text}"

        if not document_texts:
            ProjectManager.delete_project(project.project_id)
            return jsonify({
                "success": False,
                "error": "No documents could be processed. Check the file formats and try again."
            }), 400

        project.total_text_length = len(all_text)
        ProjectManager.save_extracted_text(project.project_id, all_text)
        logger.info("Extracted %d characters from uploaded files", len(all_text))

        generator = OntologyGenerator()
        ontology = generator.generate(
            document_texts=document_texts,
            simulation_requirement=simulation_requirement,
            additional_context=additional_context if additional_context else None
        )

        entity_count = len(ontology.get("entity_types", []))
        edge_count = len(ontology.get("edge_types", []))
        logger.info("Ontology ready: %d entity types, %d edge types", entity_count, edge_count)

        project.ontology = {
            "entity_types": ontology.get("entity_types", []),
            "edge_types": ontology.get("edge_types", [])
        }
        project.analysis_summary = ontology.get("analysis_summary", "")
        project.status = ProjectStatus.ONTOLOGY_GENERATED
        ProjectManager.save_project(project)

        return jsonify({
            "success": True,
            "data": {
                "project_id": project.project_id,
                "project_name": project.name,
                "ontology": project.ontology,
                "analysis_summary": project.analysis_summary,
                "files": project.files,
                "total_text_length": project.total_text_length
            }
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


# ── Graph build ───────────────────────────────────────────────────────────────

@graph_bp.route('/build', methods=['POST'])
@limiter.limit("10 per hour")
def build_graph():
    """
    Start an async graph build for a project that already has an ontology.

    JSON body:
      project_id   — (required)
      graph_name   — (optional)
      chunk_size   — (optional, default from config)
      chunk_overlap— (optional, default from config)
      force        — (optional bool) rebuild even if a build is in progress
    """
    try:
        logger.info("Starting graph build")

        if not Config.ZEP_API_KEY:
            return jsonify({"success": False, "error": "ZEP_API_KEY is not configured"}), 500

        data = request.get_json() or {}
        project_id = data.get('project_id')

        if not project_id:
            return jsonify({"success": False, "error": "project_id is required"}), 400

        project = ProjectManager.get_project(project_id)
        if not project:
            return jsonify({"success": False, "error": f"Project not found: {project_id}"}), 404

        force = data.get('force', False)

        if project.status == ProjectStatus.CREATED:
            return jsonify({"success": False, "error": "Generate the ontology before building the graph"}), 400

        if project.status == ProjectStatus.GRAPH_BUILDING and not force:
            return jsonify({
                "success": False,
                "error": "A graph build is already in progress. Pass force=true to rebuild.",
                "task_id": project.graph_build_task_id
            }), 400

        if force and project.status in [ProjectStatus.GRAPH_BUILDING, ProjectStatus.FAILED, ProjectStatus.GRAPH_COMPLETED]:
            project.status = ProjectStatus.ONTOLOGY_GENERATED
            project.graph_id = None
            project.graph_build_task_id = None
            project.error = None

        graph_name = data.get('graph_name', project.name or 'EchoSim Graph')
        chunk_size = data.get('chunk_size', project.chunk_size or Config.DEFAULT_CHUNK_SIZE)
        chunk_overlap = data.get('chunk_overlap', project.chunk_overlap or Config.DEFAULT_CHUNK_OVERLAP)
        project.chunk_size = chunk_size
        project.chunk_overlap = chunk_overlap

        text = ProjectManager.get_extracted_text(project_id)
        if not text:
            return jsonify({"success": False, "error": "Extracted project text was not found"}), 400

        ontology = project.ontology
        if not ontology:
            return jsonify({"success": False, "error": "Ontology data was not found"}), 400

        task_manager = TaskManager()
        task_id = task_manager.create_task(
            task_type="graph_build",
            metadata={"graph_name": graph_name, "project_id": project_id},
        )
        logger.info("Graph build task created: task_id=%s project_id=%s", task_id, project_id)

        project.status = ProjectStatus.GRAPH_BUILDING
        project.graph_build_task_id = task_id
        ProjectManager.save_project(project)

        def build_task():
            build_logger = get_logger('mirofish.build')
            try:
                build_logger.info("[%s] Graph build started", task_id)
                task_manager.update_task(task_id, status=TaskStatus.PROCESSING, message="Initializing")

                builder = GraphBuilderService(api_key=Config.ZEP_API_KEY)

                task_manager.update_task(task_id, message="Chunking source text", progress=5)
                chunks = TextProcessor.split_text(text, chunk_size=chunk_size, overlap=chunk_overlap)
                total_chunks = len(chunks)

                task_manager.update_task(task_id, message="Creating graph in Zep", progress=10)
                graph_id = builder.create_graph(name=graph_name)
                project.graph_id = graph_id
                ProjectManager.save_project(project)

                task_manager.update_task(task_id, message="Applying ontology", progress=15)
                builder.set_ontology(graph_id, ontology)

                def add_progress_callback(msg, progress_ratio):
                    task_manager.update_task(task_id, message=msg, progress=15 + int(progress_ratio * 40))

                task_manager.update_task(task_id, message=f"Uploading {total_chunks} text chunks", progress=15)
                episode_uuids = builder.add_text_batches(
                    graph_id, chunks, batch_size=3, progress_callback=add_progress_callback
                )

                task_manager.update_task(task_id, message="Waiting for Zep to process chunks", progress=55)

                def wait_progress_callback(msg, progress_ratio):
                    task_manager.update_task(task_id, message=msg, progress=55 + int(progress_ratio * 35))

                builder._wait_for_episodes(episode_uuids, wait_progress_callback)

                task_manager.update_task(task_id, message="Fetching graph summary", progress=95)
                graph_data = builder.get_graph_data(graph_id)

                project.status = ProjectStatus.GRAPH_COMPLETED
                ProjectManager.save_project(project)

                node_count = graph_data.get("node_count", 0)
                edge_count = graph_data.get("edge_count", 0)
                build_logger.info("[%s] Graph build complete: graph_id=%s nodes=%d edges=%d",
                                  task_id, graph_id, node_count, edge_count)

                task_manager.update_task(
                    task_id,
                    status=TaskStatus.COMPLETED,
                    message="Graph build complete",
                    progress=100,
                    result={
                        "project_id": project_id,
                        "graph_id": graph_id,
                        "node_count": node_count,
                        "edge_count": edge_count,
                        "chunk_count": total_chunks
                    }
                )

            except Exception as e:
                build_logger.error("[%s] Graph build failed: %s", task_id, e)
                build_logger.debug(traceback.format_exc())
                project.status = ProjectStatus.FAILED
                project.error = str(e)
                ProjectManager.save_project(project)
                task_manager.update_task(
                    task_id,
                    status=TaskStatus.FAILED,
                    message=f"Graph build failed: {e}",
                    error=traceback.format_exc()
                )

        threading.Thread(target=build_task, daemon=True).start()

        return jsonify({
            "success": True,
            "data": {
                "project_id": project_id,
                "task_id": task_id,
                "message": "Graph build started. Poll /task/{task_id} for progress."
            }
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


# ── Task status ───────────────────────────────────────────────────────────────

@graph_bp.route('/task/<task_id>', methods=['GET'])
def get_task(task_id: str):
    """Return the status and result of a background task."""
    task = TaskManager().get_task(task_id)
    
    if not task:
        return jsonify({
            "success": False,
            "error": f"Task not found: {task_id}"
        }), 404
    
    return jsonify({
        "success": True,
        "data": task.to_dict()
    })


@graph_bp.route('/tasks', methods=['GET'])
def list_tasks():
    """List all background tasks."""
    tasks = TaskManager().list_tasks()

    return jsonify({
        "success": True,
        "data": tasks,
        "count": len(tasks)
    })


# ── Graph data ────────────────────────────────────────────────────────────────

@graph_bp.route('/data/<graph_id>', methods=['GET'])
def get_graph_data(graph_id: str):
    """Return nodes and edges for a Zep graph."""
    try:
        if not Config.ZEP_API_KEY:
            return jsonify({
                "success": False,
                "error": "ZEP_API_KEY is required"
            }), 500
        
        builder = GraphBuilderService(api_key=Config.ZEP_API_KEY)
        graph_data = builder.get_graph_data(graph_id)
        
        return jsonify({
            "success": True,
            "data": graph_data
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@graph_bp.route('/delete/<graph_id>', methods=['DELETE'])
def delete_graph(graph_id: str):
    """Delete a Zep graph by ID."""
    try:
        if not Config.ZEP_API_KEY:
            return jsonify({
                "success": False,
                "error": "ZEP_API_KEY is required"
            }), 500
        
        builder = GraphBuilderService(api_key=Config.ZEP_API_KEY)
        builder.delete_graph(graph_id)
        
        return jsonify({
            "success": True,
            "message": f"Graph deleted: {graph_id}"
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500
