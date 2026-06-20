import json
from pathlib import Path

from app.services.archetype_library import ARCHETYPE_DEFINITIONS
from app.services.sentiment_analyzer import SentimentAnalyzer


def _write_jsonl(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8') as handle:
        for row in rows:
            handle.write(json.dumps(row) + '\n')


def test_sentiment_analysis_cache_hits_and_invalidates(monkeypatch, tmp_path, testing_env):
    archetype_key = next(iter(ARCHETYPE_DEFINITIONS.keys()))
    sim_dir = tmp_path / 'sim_123'
    sim_dir.mkdir(parents=True, exist_ok=True)
    (sim_dir / 'archetype_map.json').write_text(
        json.dumps([{'agent_id': 1, 'archetype': archetype_key}]),
        encoding='utf-8',
    )

    actions_path = sim_dir / 'actions.jsonl'
    _write_jsonl(
        actions_path,
        [
            {
                'round_num': 1,
                'agent_id': 1,
                'action_type': 'CREATE_POST',
                'action_args': {'content': 'The launch looks promising.'},
            }
        ],
    )

    classify_calls = {'count': 0}

    def fake_classify(self, posts):
        classify_calls['count'] += 1
        # _classify_batch returns (scores, topics, success)
        return [0.6 for _ in posts], [['features'] for _ in posts], True

    monkeypatch.setattr(SentimentAnalyzer, '_classify_batch', fake_classify)
    monkeypatch.setattr(SentimentAnalyzer, '_extract_top_objections', lambda self, posts: [])

    analyzer = SentimentAnalyzer('sim_123')
    analyzer._sim_dir = str(sim_dir)

    first = analyzer.analyze_all()
    second = analyzer.analyze_all()

    assert first['overall']['avg_score'] == second['overall']['avg_score']
    assert classify_calls['count'] == 1

    _write_jsonl(
        actions_path,
        [
            {
                'round_num': 1,
                'agent_id': 1,
                'action_type': 'CREATE_POST',
                'action_args': {'content': 'The launch looks promising.'},
            },
            {
                'round_num': 2,
                'agent_id': 1,
                'action_type': 'CREATE_POST',
                'action_args': {'content': 'Pricing is getting harder to defend.'},
            },
        ],
    )

    third = analyzer.analyze_all()

    assert third['total_posts_analyzed'] == 2
    assert classify_calls['count'] == 2
