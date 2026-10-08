"""Passive skill tree: shape, text, points, validation, storage and refunds, on disposable databases."""
from datetime import datetime, timedelta, timezone
import json
import math
import os
from pathlib import Path
import random
import sqlite3
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
import game
import game_tree as tree
from courses import COURSES, LESSONS

STAMP = '2026-10-05T22:00:00+00:00'


def progress(lessons=()):
    return dict(completed={l['id']: dict(at=STAMP, xp=l['xp']) for l in lessons},
                projects=[], projectState={}, readingState={}, guides=[], revealed={})


def course_lessons(cid):
    return [l for l in LESSONS if l['course'] == cid]


class TreeShapeTests(unittest.TestCase):
    def test_counts_layout_and_links(self):
        kinds = {}
        for node in tree.NODES.values():
            kinds[node['kind']] = kinds.get(node['kind'], 0) + 1
        self.assertEqual(len(tree.NODES), 120)
        self.assertEqual(kinds, dict(start=12, small=84, notable=20, keystone=4))
        self.assertEqual(set(tree.START_BY_CLASS), {c['id'] for c in game.CLASSES})
        for node in tree.NODES.values():
            self.assertLessEqual(math.hypot(node['x'], node['y']), tree.RADIUS + .5, node['id'])
            for other in node['links']:
                self.assertIn(node['id'], tree.NODES[other]['links'])
        self.assertEqual(tree.reachable('start-warrior', set(tree.NODES)), set(tree.NODES))
        # Class starts are leaves: no build can pass through another class's start.
        for start in tree.STARTS:
            self.assertEqual(len(tree.ADJACENCY[start]), 1)

    def test_keystones_sit_between_sectors_eight_points_from_the_nearest_classes(self):
        for kid, _, before, after, _ in tree.KEYSTONES:
            near = [s['classes'][2] for s in tree.SECTORS if s['id'] == before] + \
                   [s['classes'][0] for s in tree.SECTORS if s['id'] == after]
            for cls in near:
                self.assertEqual(len(tree.path_to(cls, {tree.START_BY_CLASS[cls]}, kid)), 8, (cls, kid))
            centre = [s['classes'][1] for s in tree.SECTORS if s['id'] == before][0]
            self.assertEqual(len(tree.path_to(centre, {tree.START_BY_CLASS[centre]}, kid)), 10)

    def test_every_node_is_reachable_from_every_class_and_lateral_links_allow_hybrids(self):
        for cls, start in tree.START_BY_CLASS.items():
            for nid in tree.NODES:
                path = tree.path_to(cls, {start}, nid)
                if nid in tree.STARTS and nid != start:
                    self.assertIsNone(path)
                else:
                    self.assertIsNotNone(path, (cls, nid))
        # A Warrior reaches the Skirmisher sector over the outer bridge without taking a keystone.
        path = tree.path_to('deathknight', {'start-deathknight'}, 'demonhunter-3')
        self.assertFalse(set(path) & {k[0] for k in tree.KEYSTONES})
        self.assertIn('vanguard-bridge', path)

    def test_text_comes_from_the_effects_and_keystones_have_a_cost(self):
        costs = {'castCost', 'healingLess', 'minionLess', 'hitLess', 'damageLess', 'noCrit'}
        for node in tree.NODES.values():
            self.assertTrue(set(node['mods']) <= tree.MOD_KEYS, node['id'])
            self.assertEqual(node['text'], tree.describe(node['mods']))
            if node['kind'] in ('small', 'notable', 'keystone'):
                self.assertTrue(node['text'], node['id'])
            if node['kind'] == 'keystone':
                self.assertTrue(set(node['mods']) & costs, node['id'])
        self.assertIn('Armor counts double', tree.NODES['living-fortress']['text'])

    def test_names_are_our_own(self):
        names = [n['name'] for n in tree.NODES.values() if n['kind'] in ('notable', 'keystone')]
        names += [name for name, _ in tree.SMALL.values()]
        self.assertEqual(len(names), len(set(names)))
        borrowed = ('blood magic', 'blood pact', 'iron reflexes', 'chaos inoculation', 'eldritch battery',
                    'resolute technique', 'mind over matter', 'avatar of fire', 'elemental overload',
                    'acrobatics', 'unwavering stance', 'vaal pact', 'iron will', 'iron grip', 'zealot',
                    'shield wall', 'shadow dance', 'lifebloom', 'flurry', 'soul siphon', 'siegebreaker',
                    'wildfire', 'pyromancy', 'spellweaver', 'arcane tempo', 'iron oath', 'executioner',
                    'precision', 'bloodletter', 'scatter shot', 'final verdict')
        for name in names:
            self.assertNotIn(name.lower(), borrowed)

    def test_catalog_carries_the_tree(self):
        tree_catalog = game.catalog()['tree']
        self.assertEqual(len(tree_catalog['nodes']), 120)
        self.assertEqual([s['id'] for s in tree_catalog['sectors']], ['vanguard', 'skirmisher', 'wilds', 'arcane'])
        json.dumps(tree_catalog)


class PassiveTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='ml-game-tree-')
        self.db = sqlite3.connect(Path(self.tmp.name) / 'game.sqlite3')
        game.ensure_schema(self.db)
        # Six Python foundations lessons: level 7 and one mastered path, so 7 points.
        self.progress = progress(course_lessons('foundations'))
        self.action('hero', dict(name='Durgan', race='orc', **{'class': 'warrior'}))

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def action(self, action, body):
        return game.handle(self.db, action, body, self.progress, random.Random(5))

    def allocate(self, nodes):
        return self.action('passives', dict(allocated=nodes))['game']['passives']

    def state(self):
        return game.state(self.db, self.progress)

    def test_points_are_levels_after_the_first_plus_mastered_paths(self):
        self.assertEqual(game.passive_points(progress()), 0)
        self.assertEqual(game.passive_points(progress(LESSONS[:1])), 1)
        self.assertEqual(game.passive_points(self.progress), 6 + 1)
        self.assertEqual(game.passive_points(progress(LESSONS)), 59 + len(COURSES))
        self.assertEqual(self.state()['passives'], dict(
            allocated=['start-warrior'], points=dict(earned=7, spent=0, available=7), refunded=None))

    def test_allocate_respec_and_refund_all_are_free(self):
        spoke = ['start-warrior', 'warrior-1', 'warrior-2', 'warrior-3', 'breakthrough']
        saved = self.allocate(spoke)
        self.assertEqual(saved['allocated'], sorted(spoke))
        self.assertEqual(saved['points'], dict(earned=7, spent=4, available=3))
        other = ['start-warrior', 'warrior-1', 'warrior-2', 'vanguard-link-paladin-warrior', 'paladin-2',
                 'paladin-3', 'rampart-oath', 'vanguard-inner-1']
        self.assertEqual(self.allocate(other)['points']['spent'], 7)
        self.assertEqual(self.allocate(['start-warrior'])['points'], dict(earned=7, spent=0, available=7))
        stored = json.loads(self.db.execute("SELECT value FROM game_meta WHERE key='passives'").fetchone()[0])
        self.assertEqual(stored, {'v': 1, 'nodes': []})

    def test_invalid_allocations_are_rejected_and_change_nothing(self):
        self.allocate(['start-warrior', 'warrior-1'])
        before = self.state()
        cases = {
            'unknown id': ['start-warrior', 'warrior-1', 'no-such-node'],
            'missing start': ['warrior-1', 'warrior-2'],
            'other class start': ['start-warrior', 'start-paladin'],
            'disconnected': ['start-warrior', 'warrior-1', 'breakthrough'],
            'disconnected far': ['start-warrior', 'blood-bargain'],
            'too many points': ['start-warrior', 'warrior-1', 'warrior-2', 'warrior-3', 'breakthrough',
                                'vanguard-inner-2', 'unbowed', 'vanguard-inner-1', 'rampart-oath'],
            'duplicates': ['start-warrior', 'warrior-1', 'warrior-1'],
            'empty': [],
            'not a list': 'start-warrior',
            'not strings': ['start-warrior', 7],
            'too long': ['start-warrior'] + ['x' * 65],
        }
        for label, nodes in cases.items():
            with self.subTest(label):
                with self.assertRaises(ValueError):
                    self.allocate(nodes)
        with self.assertRaises(ValueError):
            self.action('passives', {})
        self.assertEqual(self.state(), before)

    def test_a_running_fight_blocks_changes_but_a_stale_one_does_not(self):
        self.action('battle/start', {})
        with self.assertRaisesRegex(ValueError, 'fight'):
            self.allocate(['start-warrior', 'warrior-1'])
        old = (datetime.now(timezone.utc) - timedelta(minutes=16)).isoformat()
        with self.db:
            self.db.execute("UPDATE game_battles SET started=? WHERE outcome='active'", (old,))
        self.assertEqual(self.allocate(['start-warrior', 'warrior-1'])['points']['spent'], 1)
        battle = self.action('battle/start', {})['battle']
        self.action('battle/finish', dict(battleId=battle['id'], outcome='retreat', bossDamage=0, kills=0, seconds=3))
        self.assertEqual(self.allocate(['start-warrior'])['points']['spent'], 0)

    def test_no_hero_no_passives(self):
        self.action('retire', dict(confirm='RETIRE'))
        self.assertIsNone(self.state()['passives'])
        with self.assertRaisesRegex(ValueError, 'hero'):
            self.allocate(['start-warrior'])

    def test_older_databases_get_the_default_and_backups_carry_passives(self):
        # A database from before the tree has no passives row at all.
        self.assertIsNone(self.db.execute("SELECT 1 FROM game_meta WHERE key='passives'").fetchone())
        self.assertEqual(game.metadata(self.db)['passives'], {'v': 1, 'nodes': []})
        self.assertEqual(game.export(self.db)['meta']['passives'], {'v': 1, 'nodes': []})
        self.allocate(['start-warrior', 'warrior-1', 'warrior-2'])
        self.assertEqual(game.export(self.db)['meta']['passives'], {'v': 1, 'nodes': ['warrior-1', 'warrior-2']})
        self.action('retire', dict(confirm='RETIRE'))
        self.assertEqual(game.metadata(self.db)['passives'], {'v': 1, 'nodes': []})

    def test_a_saved_build_that_no_longer_fits_is_refunded_whole(self):
        cases = {
            'changed': [{'v': 1, 'nodes': ['warrior-1', 'renamed-node']},
                        {'v': 2, 'nodes': ['warrior-1']},
                        {'v': 1, 'nodes': 'warrior-1'},
                        {'v': 1, 'nodes': [1, 2]},
                        ['warrior-1'],
                        {'v': 1, 'nodes': ['warrior-1', 'breakthrough']},
                        {'v': 1, 'nodes': ['start-paladin', 'paladin-1']}],
            'points': [{'v': 1, 'nodes': ['warrior-1', 'warrior-2', 'warrior-3', 'breakthrough',
                                          'vanguard-inner-2', 'unbowed', 'vanguard-inner-1', 'rampart-oath']}],
        }
        for reason, values in cases.items():
            for value in values:
                with self.subTest(value=value):
                    with self.db:
                        game.put_meta(self.db, 'passives', value)
                    passives = self.state()['passives']
                    self.assertEqual(passives['allocated'], ['start-warrior'])
                    self.assertEqual(passives['points'], dict(earned=7, spent=0, available=7))
                    self.assertEqual(passives['refunded'], reason)
        # Saving a new build clears the notice.
        self.assertIsNone(self.allocate(['start-warrior', 'warrior-1'])['refunded'])

    def test_losing_progress_refunds_instead_of_overspending(self):
        self.allocate(['start-warrior', 'warrior-1', 'warrior-2', 'warrior-3', 'breakthrough'])
        self.progress = progress(course_lessons('foundations')[:2])
        passives = self.state()['passives']
        self.assertEqual((passives['refunded'], passives['points']['spent']), ('points', 0))

    def test_a_refund_stays_when_the_points_come_back(self):
        build = ['start-warrior', 'warrior-1', 'warrior-2', 'warrior-3', 'breakthrough']
        self.allocate(build)
        full, self.progress = self.progress, progress(course_lessons('foundations')[:2])
        # Any game action stores the refund.
        self.action('settings', dict(enabled=True))
        self.progress = full
        passives = self.state()['passives']
        self.assertEqual((passives['allocated'], passives['refunded']), (['start-warrior'], 'points'))
        self.assertEqual(passives['points'], dict(earned=7, spent=0, available=7))
        self.assertIsNone(self.allocate(build)['refunded'])

    def test_the_server_stores_a_refund_when_it_starts(self):
        # An update can cost a saved build its points, for example a new lesson in a mastered path.
        build = ['start-warrior', 'warrior-1', 'warrior-2', 'warrior-3', 'breakthrough']
        self.allocate(build)
        data = Path(self.tmp.name) / 'data'
        data.mkdir()
        db = sqlite3.connect(data / 'workshop.sqlite3')
        self.db.backup(db)
        with db:
            db.execute('CREATE TABLE completions (lesson TEXT PRIMARY KEY, at TEXT, xp INTEGER)')
            db.executemany('INSERT INTO completions VALUES (?,?,?)',
                           [(l['id'], STAMP, l['xp']) for l in course_lessons('foundations')[:2]])
        db.close()
        code = 'import sys;sys.path.insert(0,sys.argv[1]);import server;server.open_data()'
        subprocess.run([sys.executable, '-c', code, str(ROOT / 'backend')], check=True, timeout=120,
                       env={**os.environ, 'ML_WORKSHOP_DATA_DIR': str(data)})
        db = sqlite3.connect(data / 'workshop.sqlite3')
        try:
            stored = json.loads(db.execute("SELECT value FROM game_meta WHERE key='passives'").fetchone()[0])
        finally:
            db.close()
        self.assertEqual(stored, {'v': 1, 'nodes': [], 'refunded': 'points'})


if __name__ == '__main__':
    unittest.main()
