import threading
import time

import pytest

from app import create_app
from app.models.task import TaskManager, TaskStatus
from app.services.campaign_manager import CampaignStatus


class CampaignRecord:
    def __init__(self, payload):
        self.payload = payload

    def to_dict(self):
        return dict(self.payload)


class FakeCampaignManager:
    def __init__(self):
        self.campaigns = {}
        # Test hook: when set, inject_scenario_event returns this instead of a
        # synthesized success — used to exercise the failed-injection path.
        self.next_inject_result = None

    def create_campaign(self, project_id, graph_id, seed_data, **kwargs):
        campaign_id = f'camp_{len(self.campaigns) + 1}'
        payload = {
            'campaign_id': campaign_id,
            'project_id': project_id,
            'graph_id': graph_id,
            'seed_data': seed_data,
            'sim_id_a': 'sim_a',
            'sim_id_b': 'sim_b',
            'sim_id_c': 'sim_c',
            'status': CampaignStatus.CREATED.value,
            'competitive_event_type': 'price_drop',
            'crisis_event_type': 'security_breach',
            'competitive_event_weights': seed_data.get('competitive_event_weights', {}),
            'crisis_event_weights': seed_data.get('crisis_event_weights', {}),
            'scenario_b_inject_round': 7,
            'scenario_c_inject_round': 14,
            'scenario_b_injected': False,
            'scenario_c_injected': False,
            'total_agents': kwargs.get('total_agents', 50),
            'prepare_task_id': '',
            'prepare_progress': 0,
            'prepare_message': '',
            'pending_injections': [],
            'error': None,
            'created_at': '2026-03-21T00:00:00',
            'updated_at': '2026-03-21T00:00:00',
        }
        self.campaigns[campaign_id] = payload
        return CampaignRecord(payload)

    def start_prepare(self, campaign_id):
        payload = self.campaigns[campaign_id]
        task_id = TaskManager().create_task('campaign_prepare', {'campaign_id': campaign_id})
        payload['status'] = CampaignStatus.PREPARING.value
        payload['prepare_task_id'] = task_id
        payload['prepare_progress'] = 5
        payload['prepare_message'] = 'Preparing scenario inputs'

        def complete_task():
            TaskManager().update_task(
                task_id,
                status=TaskStatus.PROCESSING,
                progress=65,
                message='Generating profiles',
            )
            time.sleep(0.02)
            payload['status'] = CampaignStatus.READY.value
            payload['prepare_progress'] = 100
            payload['prepare_message'] = 'Scenario preparation complete'
            TaskManager().complete_task(
                task_id,
                {'campaign': dict(payload)},
                message='Scenario preparation complete',
            )

        threading.Thread(target=complete_task, daemon=True).start()
        return {'campaign': CampaignRecord(payload), 'task': TaskManager().get_task(task_id).to_dict()}

    def get_prepare_status(self, campaign_id, task_id=None):
        payload = self.campaigns[campaign_id]
        task = TaskManager().get_task(task_id or payload['prepare_task_id'])
        return {'campaign': dict(payload), 'task': task.to_dict()}

    def start_campaign(self, campaign_id, platform='parallel', max_rounds=20):
        payload = self.campaigns[campaign_id]
        payload['status'] = CampaignStatus.RUNNING.value
        payload['max_rounds'] = max_rounds
        return CampaignRecord(payload)

    def get_campaign_status(self, campaign_id):
        payload = dict(self.campaigns[campaign_id])
        recent_actions = [
            {
                'agent_name': 'Agent One',
                'action_type': 'CREATE_POST',
                'round_num': 2,
            }
        ]
        return {
            'campaign': payload,
            'scenario_a': {'runner_status': 'running', 'current_round': 2, 'total_rounds': 20, 'recent_actions': recent_actions},
            'scenario_b': {'runner_status': 'running', 'current_round': 2, 'total_rounds': 20, 'recent_actions': recent_actions},
            'scenario_c': {'runner_status': 'running', 'current_round': 2, 'total_rounds': 20, 'recent_actions': recent_actions},
        }

    def list_campaigns(self):
        return list(self.campaigns.values())

    def inject_scenario_event(self, campaign_id, scenario, **kwargs):
        payload = self.campaigns[campaign_id]
        if self.next_inject_result is not None:
            return self.next_inject_result
        if scenario == 'b':
            payload['scenario_b_injected'] = True
        if scenario == 'c':
            payload['scenario_c_injected'] = True
        return {'success': True, 'scenario': scenario, 'status': 'injected'}


class FakeSentimentAnalyzer:
    def __init__(self, simulation_id, **kwargs):
        self.simulation_id = simulation_id

    def analyze_all(self):
        return {
            'simulation_id': self.simulation_id,
            'total_posts_analyzed': 2,
            'overall': {
                'avg_score': 0.42,
                'weighted_avg_score': 0.5,
                'nps_score': 25.0,
                'positive': 2,
                'negative': 0,
                'neutral': 0,
                'positive_pct': 100.0,
                'negative_pct': 0.0,
                'neutral_pct': 0.0,
            },
            'timeline': [{'round_num': 1, 'avg_score': 0.42}],
            'factions': {'advocates': 1, 'detractors': 0, 'neutral': 0, 'churned': 0, 'advocates_pct': 100.0, 'detractors_pct': 0.0, 'neutral_pct': 0.0, 'churned_pct': 0.0},
            'top_objections': [],
            'persona_heatmap': {},
        }


@pytest.fixture
def client(testing_env, monkeypatch):
    from app.api import sentiment as sentiment_api

    app = create_app(testing_env)
    app.testing = True

    monkeypatch.setattr(sentiment_api, '_campaign_manager', FakeCampaignManager())
    monkeypatch.setattr(sentiment_api, 'SentimentAnalyzer', FakeSentimentAnalyzer)
    monkeypatch.setattr(
        sentiment_api,
        'compare_scenarios',
        lambda sim_a, sim_b, sim_c: {
            'rounds': [1, 2],
            'scenario_a': [0.1, 0.2],
            'scenario_b': [0.1, 0.0],
            'scenario_c': [0.1, -0.2],
            'details': {
                'a': {'overall': {'avg_score': 0.2}, 'factions': {'advocates_pct': 60.0, 'detractors_pct': 10.0}},
                'b': {'overall': {'avg_score': 0.0}, 'factions': {'advocates_pct': 40.0, 'detractors_pct': 30.0}},
                'c': {'overall': {'avg_score': -0.2}, 'factions': {'advocates_pct': 20.0, 'detractors_pct': 50.0}},
            },
        },
    )

    return app.test_client()


def _valid_seed():
    return {
        'product_name': 'Signal Desk',
        'product_category': 'B2B SaaS',
        'tagline': 'Run launch decisions with evidence',
        'target_market': 'Product marketers at software companies',
        'core_features': [{'name': 'Launch monitoring', 'description': 'Tracks market reaction'}],
        'pricing_tiers': [{'name': 'Growth', 'price': '$99', 'description': 'Small teams'}],
        'competitive_event_weights': {'price_drop': 40, 'feature_match': 30, 'comparison_campaign': 30},
        'crisis_event_weights': {'security_breach': 40, 'harsh_review': 30, 'misleading_comparison': 30},
    }


def test_campaign_prepare_poll_start_and_sentiment_routes(client):
    create_response = client.post(
        '/api/sentiment/campaign/create',
        json={'project_id': 'proj_1', 'graph_id': 'graph_1', 'seed_data': _valid_seed()},
    )
    assert create_response.status_code == 200
    campaign_id = create_response.get_json()['campaign']['campaign_id']

    prepare_response = client.post(f'/api/sentiment/campaign/{campaign_id}/prepare')
    prepare_payload = prepare_response.get_json()
    assert prepare_response.status_code == 200
    assert prepare_payload['task_id']

    task_id = prepare_payload['task_id']
    final_status = None
    for _ in range(10):
        status_response = client.get(f'/api/sentiment/campaign/{campaign_id}/prepare/status', query_string={'task_id': task_id})
        assert status_response.status_code == 200
        final_status = status_response.get_json()['task']['status']
        if final_status == 'completed':
            break
        time.sleep(0.02)
    assert final_status == 'completed'

    start_response = client.post(f'/api/sentiment/campaign/{campaign_id}/start', json={'max_rounds': 20})
    assert start_response.status_code == 200
    assert start_response.get_json()['campaign']['status'] == 'running'

    status_response = client.get(f'/api/sentiment/campaign/{campaign_id}')
    status_payload = status_response.get_json()
    assert status_response.status_code == 200
    assert status_payload['scenario_a']['recent_actions'][0]['agent_name'] == 'Agent One'

    sentiment_response = client.get(f'/api/sentiment/campaign/{campaign_id}/sentiment')
    assert sentiment_response.status_code == 200
    assert sentiment_response.get_json()['scenario_a']['overall']['avg_score'] == 0.42

    compare_response = client.get(f'/api/sentiment/campaign/{campaign_id}/compare')
    assert compare_response.status_code == 200
    assert compare_response.get_json()['comparison']['rounds'] == [1, 2]


def test_inject_event_route_reports_success(client):
    from app.api import sentiment as sentiment_api

    create_response = client.post(
        '/api/sentiment/campaign/create',
        json={'project_id': 'proj_1', 'graph_id': 'graph_1', 'seed_data': _valid_seed()},
    )
    campaign_id = create_response.get_json()['campaign']['campaign_id']

    inject_response = client.post(
        f'/api/sentiment/campaign/{campaign_id}/inject',
        json={'scenario': 'b', 'custom_prompt': 'Breaking news!'},
    )
    assert inject_response.status_code == 200
    payload = inject_response.get_json()
    assert payload['success'] is True
    assert payload['result']['success'] is True


def test_inject_event_route_propagates_failure(client):
    """A no-op injection (e.g. the sim env wasn't reachable) must not be
    reported as an HTTP success — this previously let the UI show "Event
    injected successfully" for injections that silently did nothing."""
    from app.api import sentiment as sentiment_api

    create_response = client.post(
        '/api/sentiment/campaign/create',
        json={'project_id': 'proj_1', 'graph_id': 'graph_1', 'seed_data': _valid_seed()},
    )
    campaign_id = create_response.get_json()['campaign']['campaign_id']

    sentiment_api._campaign_manager.next_inject_result = {
        'success': False,
        'error': 'Simulation environment is not running or has closed, cannot perform Interview',
    }

    inject_response = client.post(
        f'/api/sentiment/campaign/{campaign_id}/inject',
        json={'scenario': 'b', 'custom_prompt': 'Breaking news!'},
    )
    assert inject_response.status_code == 502
    payload = inject_response.get_json()
    assert payload['success'] is False
    assert 'not running' in payload['error']


def test_report_status_route_accepts_get_query(client):
    task_id = TaskManager().create_task('report_generate', {'simulation_id': 'sim_1'})
    TaskManager().update_task(
        task_id,
        status=TaskStatus.PROCESSING,
        progress=30,
        message='Generating report',
    )

    response = client.get('/api/report/generate/status', query_string={'task_id': task_id})

    assert response.status_code == 200
    payload = response.get_json()['data']
    assert payload['task_id'] == task_id
    assert payload['progress'] == 30
    assert payload['message'] == 'Generating report'
