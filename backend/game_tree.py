"""The hero's passive skill tree: 120 nodes on a circle, sent to the client in the game catalog.

Four sectors of three classes each. Every class starts on the outer ring and walks inward along
its own spoke to a notable; lateral links join the spokes of a sector, an outer bridge joins
neighbouring sectors, and a keystone sits on each sector boundary, reachable from both sides.

Node effects are plain numbers (`mods`); the client sums them and the battle engine reads the
sums. The tooltip text is generated from the same numbers, so the two cannot drift apart.
Node ids are stable: a saved allocation that names an id that no longer exists is refunded.
"""
from collections import deque
import math

RADIUS = 600
SECTORS = [
    dict(id='vanguard', name='Vanguard', angle=-90, classes=['paladin', 'warrior', 'deathknight'],
         text='Health, armor and close-range power.'),
    dict(id='skirmisher', name='Skirmisher', angle=0, classes=['demonhunter', 'rogue', 'monk'],
         text='Critical strikes, haste and quick movement.'),
    dict(id='wilds', name='Wilds', angle=90, classes=['hunter', 'druid', 'shaman'],
         text='Projectiles, ground zones, chains and healing.'),
    dict(id='arcane', name='Arcane', angle=180, classes=['warlock', 'mage', 'priest'],
         text='Ability damage, burns, cooldowns and shields.'),
]

# Small node types: name and effect. Ratings add to the gear totals and go through the same
# diminishing returns, so the stat sheet shows them like gear.
SMALL = dict(
    might=('Might', dict(flatPower=2)),
    vigor=('Vigor', dict(flatHp=8)),
    sharp=('Sharp Eye', dict(critRating=3)),
    swift=('Swiftness', dict(hasteRating=3)),
    technique=('Technique', dict(masteryRating=3)),
    reach=('Reach', dict(area=.02)),
    kindling=('Kindling', dict(burn=.025)),
    grit=('Grit', dict(versRating=3)),
    renewal=('Renewal', dict(healing=.015)),
    flow=('Flow', dict(cdr=.01)),
)

# Notables per sector, in template order: left spoke, centre spoke, right spoke, inner left, inner right.
NOTABLES = dict(
    vanguard=[
        ('rampart-oath', 'Rampart Oath', dict(armor=.04, buffShield=.02)),
        ('breakthrough', 'Breakthrough', dict(dashStun=.4, dashGuard=.08)),
        ('mercy-stroke', 'Mercy Stroke', dict(execute=.1)),
        ('unbowed', 'Unbowed', dict(hp=.02, telegraphGuard=.08)),
        ('fault-line', 'Fault Line', dict(spinArea=.06, spinDamage=.03)),
    ],
    skirmisher=[
        ('opening-gambit', 'Opening Gambit', dict(openingCrit=1.5)),
        ('lethal-focus', 'Lethal Focus', dict(crit=.02, critMulti=.15)),
        ('quick-hands', 'Quick Hands', dict(haste=.01, doubleStrike=10)),
        ('deep-cuts', 'Deep Cuts', dict(bleed=.08)),
        ('slip-away', 'Slip Away', dict(dodge=.02, buffDuration=.1)),
    ],
    wilds=[
        ('split-fletching', 'Split Fletching', dict(splitShots=1, splitDamage=.2)),
        ('sap-rising', 'Sap Rising', dict(healing=.015, healOverTime=.004)),
        ('storm-relay', 'Storm Relay', dict(chainBounces=1, chainFalloff=.03)),
        ('pinned-prey', 'Pinned Prey', dict(snare=.05)),
        ('fertile-ground', 'Fertile Ground', dict(zoneDuration=.12, zoneArea=.05)),
    ],
    arcane=[
        ('kindled-mind', 'Kindled Mind', dict(burn=.1, burnDuration=.5)),
        ('spell-cadence', 'Spell Cadence', dict(ability=.02, cadence=.03)),
        ('mirror-ward', 'Mirror Ward', dict(shield=.05, shieldNova=.3)),
        ('quickened-rite', 'Quickened Rite', dict(cdr=.02)),
        ('spirit-harvest', 'Spirit Harvest', dict(killHeal=.005)),
    ],
)

# Keystones on the boundary clockwise of each sector: (sector before, sector after).
KEYSTONES = [
    ('blood-bargain', 'Blood Bargain', 'vanguard', 'skirmisher',
     dict(cooldownLess=.3, castCost=.05, healingLess=.35)),
    ('tunnel-vision', 'Tunnel Vision', 'skirmisher', 'wilds',
     dict(bossMore=.2, minionLess=.4)),
    ('scorched-earth', 'Scorched Earth', 'wilds', 'arcane',
     dict(dotMore=.8, hitLess=.25)),
    ('living-fortress', 'Living Fortress', 'arcane', 'vanguard',
     dict(hpMore=.25, armorMore=1, damageLess=.3, noCrit=1)),
]

# Small node types in each sector's template slots.
SMALL_LAYOUT = dict(
    vanguard=dict(spokes=[['vigor', 'renewal', 'might'], ['might', 'vigor', 'reach'], ['might', 'grit', 'reach']],
                  links=['grit', 'vigor'], bridge='might', inner=['vigor', 'might', 'reach'],
                  ccw=['vigor', 'grit', 'vigor'], cw=['might', 'grit', 'might']),
    skirmisher=dict(spokes=[['might', 'sharp', 'swift'], ['sharp', 'might', 'sharp'], ['swift', 'swift', 'might']],
                    links=['swift', 'sharp'], bridge='sharp', inner=['sharp', 'might', 'swift'],
                    ccw=['swift', 'might', 'flow'], cw=['sharp', 'might', 'sharp']),
    wilds=dict(spokes=[['technique', 'swift', 'sharp'], ['renewal', 'technique', 'kindling'], ['technique', 'reach', 'vigor']],
               links=['reach', 'technique'], bridge='technique', inner=['swift', 'renewal', 'reach'],
               ccw=['sharp', 'technique', 'sharp'], cw=['reach', 'kindling', 'reach']),
    arcane=dict(spokes=[['kindling', 'technique', 'technique'], ['technique', 'flow', 'technique'], ['vigor', 'renewal', 'technique']],
                links=['flow', 'technique'], bridge='vigor', inner=['kindling', 'technique', 'renewal'],
                ccw=['kindling', 'technique', 'kindling'], cw=['vigor', 'grit', 'vigor']),
)

# Template positions inside a sector: (angle from the sector centre in degrees, share of RADIUS).
SPOKE_ANGLES = (-28, 0, 28)
SPOKE_DEPTHS = (.88, .76, .64)
NOTABLE_DEPTH = .52
LINK_POS = ((-14, .76), (14, .76))
BRIDGE_POS = (45, .81)
INNER_POS = ((-20, .43), (0, .43), (20, .43))
DEEP_POS = ((-10, .335), (10, .335))
CHAIN_POS = ((32, .45), (36, .385), (39, .325))
KEYSTONE_DEPTH = .225

PCT = lambda v: f'{round(abs(v) * 100, 1):g}%'
NUM = lambda v: f'{v:g}'
# One line of tooltip text per effect key.
TEXT = dict(
    flatPower=lambda v: f'+{NUM(v)} Power',
    flatHp=lambda v: f'+{NUM(v)} maximum health',
    critRating=lambda v: f'+{NUM(v)} Critical Strike',
    hasteRating=lambda v: f'+{NUM(v)} Haste',
    masteryRating=lambda v: f'+{NUM(v)} Mastery',
    versRating=lambda v: f'+{NUM(v)} Versatility',
    power=lambda v: f'+{PCT(v)} Power',
    hp=lambda v: f'+{PCT(v)} maximum health',
    crit=lambda v: f'+{PCT(v)} critical strike chance',
    haste=lambda v: f'+{PCT(v)} haste',
    ability=lambda v: f'+{PCT(v)} ability damage',
    area=lambda v: f'+{PCT(v)} area of effect',
    burn=lambda v: f'+{PCT(v)} burn damage',
    dr=lambda v: f'Take {PCT(v)} less damage',
    healing=lambda v: f'+{PCT(v)} healing received',
    cdr=lambda v: f'Cooldowns recover {PCT(v)} faster',
    armor=lambda v: f'+{PCT(v)} armor',
    buffShield=lambda v: f'Buff abilities also give a shield of {PCT(v)} of maximum health for 6 sec',
    spinArea=lambda v: f'Novas and spins cover {PCT(v)} more area',
    spinDamage=lambda v: f'Novas and spins deal {PCT(v)} more damage',
    telegraphGuard=lambda v: f'Take {PCT(v)} less damage from boss attacks marked on the ground',
    execute=lambda v: f'+{PCT(v)} damage to enemies below 30% health',
    dashStun=lambda v: f'Dashes stun enemies they hit for {NUM(v)} sec longer',
    dashGuard=lambda v: f'Take {PCT(v)} less damage for 3 sec after a dash, leap or blink',
    doubleStrike=lambda v: f'Every {NUM(v)}th auto attack strikes twice',
    openingCrit=lambda v: f'Your first hit within {NUM(v)} sec after a dash, leap or blink is a critical strike',
    critMulti=lambda v: f'Critical strikes deal {NUM(round(2 + v, 2))}× damage instead of 2×',
    dodge=lambda v: f'{PCT(v)} chance to avoid a hit',
    buffDuration=lambda v: f'Buffs last {PCT(v)} longer',
    bleed=lambda v: f'Hits make enemies bleed for {PCT(v)} of the damage over 4 sec',
    splitShots=lambda v: ('A projectile ability that hits an enemy splits off a shot at the nearest other enemy' if v == 1 else
                          f'A projectile ability that hits an enemy splits into {NUM(v)} shots at other enemies nearby'),
    splitDamage=lambda v: f'Split shots deal {PCT(v)} of the damage, with no burn or other effect',
    zoneDuration=lambda v: f'Ground zones last {PCT(v)} longer',
    zoneArea=lambda v: f'Ground zones cover {PCT(v)} more area',
    chainBounces=lambda v: f"Chain abilities jump to {NUM(v)} more {'enemy' if v == 1 else 'enemies'}",
    chainFalloff=lambda v: f'Each jump loses {PCT(.15 - v)} damage instead of 15%',
    snare=lambda v: f'+{PCT(v)} damage to rooted, stunned or slowed enemies',
    healOverTime=lambda v: f'Healing abilities also restore {PCT(v)} of maximum health per second for 5 sec',
    burnDuration=lambda v: f'Burns last {NUM(v)} sec longer',
    cadence=lambda v: f'+{PCT(v)} ability damage while another ability was cast in the last 3 sec',
    shield=lambda v: f'Shields and barriers absorb {PCT(v)} more',
    shieldNova=lambda v: f'When a shield breaks, it blasts enemies around you for {NUM(v)}× Power',
    killHeal=lambda v: f'Heal {PCT(v)} of maximum health for each kill',
    bossHitHeal=lambda v: f'Heal {PCT(v)} of maximum health when you hit a boss, at most once per second',
    cooldownLess=lambda v: f'Ability cooldowns are {PCT(v)} shorter',
    castCost=lambda v: f'Each ability costs {PCT(v)} of your current health',
    healingLess=lambda v: f'Healing and shields are {PCT(v)} weaker',
    bossMore=lambda v: f'{PCT(v)} more damage to bosses',
    minionLess=lambda v: f'{PCT(v)} less damage to all other enemies',
    dotMore=lambda v: f'Burns, bleeds and ground zones deal {PCT(v)} more damage',
    hitLess=lambda v: f'All other hits deal {PCT(v)} less damage',
    hpMore=lambda v: f'{PCT(v)} more maximum health',
    armorMore=lambda v: 'Armor counts double' if v == 1 else f'Armor counts {NUM(1 + v)}×',
    damageLess=lambda v: f'You deal {PCT(v)} less damage',
    noCrit=lambda v: 'You cannot deal critical strikes',
)
MOD_KEYS = frozenset(TEXT)


def describe(mods):
    return [TEXT[key](value) for key, value in mods.items()]


def polar(sector, angle, depth):
    theta = math.radians(sector['angle'] + angle)
    return round(math.cos(theta) * depth * RADIUS, 1), round(math.sin(theta) * depth * RADIUS, 1)


def build():
    nodes, links = {}, set()

    def add(nid, kind, name, mods, sector, pos, **extra):
        assert nid not in nodes, nid
        nodes[nid] = dict(id=nid, kind=kind, name=name, sector=sector, x=pos[0], y=pos[1],
                          mods=mods, text=describe(mods), **extra)

    def small(nid, kind, sector, pos):
        name, mods = SMALL[kind]
        add(nid, 'small', name, dict(mods), sector['id'], pos, small=kind)

    def link(a, b):
        links.add(tuple(sorted((a, b))))

    for sector in SECTORS:
        sid, layout = sector['id'], SMALL_LAYOUT[sector['id']]
        notables = NOTABLES[sid]
        for side, (cls, angle) in enumerate(zip(sector['classes'], SPOKE_ANGLES)):
            add(f'start-{cls}', 'start', '', {}, sid, polar(sector, angle, 1.), **{'class': cls})
            previous = f'start-{cls}'
            for step, (kind, depth) in enumerate(zip(layout['spokes'][side], SPOKE_DEPTHS), 1):
                small(f'{cls}-{step}', kind, sector, polar(sector, angle, depth))
                link(previous, f'{cls}-{step}')
                previous = f'{cls}-{step}'
            nid, name, mods = notables[side]
            add(nid, 'notable', name, dict(mods), sid, polar(sector, angle, NOTABLE_DEPTH))
            link(previous, nid)
        left, centre, right = sector['classes']
        for (kind, pos, (a, b)) in zip(layout['links'], LINK_POS, ((left, centre), (centre, right))):
            nid = f'{sid}-link-{a}-{b}'
            small(nid, kind, sector, polar(sector, *pos))
            link(f'{a}-2', nid)
            link(nid, f'{b}-2')
        # Two deep notables; the inner small nodes lead to them from the spoke notables above.
        for (nid, name, mods), pos in zip(notables[3:], DEEP_POS):
            add(nid, 'notable', name, dict(mods), sid, polar(sector, *pos))
        deep_left, deep_right = notables[3][0], notables[4][0]
        for index, (kind, pos, targets) in enumerate(zip(layout['inner'], INNER_POS,
                                                          ([deep_left], [deep_left, deep_right], [deep_right]))):
            nid = f'{sid}-inner-{index + 1}'
            small(nid, kind, sector, polar(sector, *pos))
            link(notables[index][0], nid)
            for target in targets:
                link(nid, target)
    # Bridges and keystone chains join each sector to the next one clockwise.
    for index, (kid, name, before, after, mods) in enumerate(KEYSTONES):
        first = next(s for s in SECTORS if s['id'] == before)
        second = next(s for s in SECTORS if s['id'] == after)
        add(kid, 'keystone', name, dict(mods), None, polar(first, 45, KEYSTONE_DEPTH),
            between=[before, after])
        bridge = f'{before}-bridge'
        small(bridge, SMALL_LAYOUT[before]['bridge'], first, polar(first, *BRIDGE_POS))
        link(f"{first['classes'][2]}-2", bridge)
        link(bridge, f"{second['classes'][0]}-2")
        for sector, chain, direction, notable in (
                (first, SMALL_LAYOUT[before]['cw'], 1, NOTABLES[before][2][0]),
                (second, SMALL_LAYOUT[after]['ccw'], -1, NOTABLES[after][0][0])):
            previous = notable
            for step, (kind, (angle, depth)) in enumerate(zip(chain, CHAIN_POS), 1):
                nid = f"{sector['id']}-{'cw' if direction == 1 else 'ccw'}-{step}"
                small(nid, kind, sector, polar(sector, angle * direction, depth))
                link(previous, nid)
                previous = nid
            link(previous, kid)
    adjacency = {nid: set() for nid in nodes}
    for a, b in links:
        adjacency[a].add(b)
        adjacency[b].add(a)
    for nid, node in nodes.items():
        node['links'] = sorted(adjacency[nid])
    return nodes, adjacency


NODES, ADJACENCY = build()
START_BY_CLASS = {node['class']: nid for nid, node in NODES.items() if node['kind'] == 'start'}
STARTS = frozenset(START_BY_CLASS.values())


def catalog():
    return dict(radius=RADIUS, nodes=list(NODES.values()),
                sectors=[{k: s[k] for k in ('id', 'name', 'angle', 'classes', 'text')} for s in SECTORS])


def reachable(start, allowed):
    """Every node in `allowed` that can be reached from `start` through `allowed`."""
    seen, queue = {start}, deque([start])
    while queue:
        for nxt in ADJACENCY[queue.popleft()]:
            if nxt in allowed and nxt not in seen:
                seen.add(nxt)
                queue.append(nxt)
    return seen


def problem(class_id, nodes, earned):
    """Why an allocation is not allowed, or None. `nodes` includes the class start."""
    start = START_BY_CLASS.get(class_id)
    unknown = [nid for nid in nodes if nid not in NODES]
    if unknown:
        return 'unknown'
    if start not in nodes:
        return 'start'
    if any(nid in STARTS and nid != start for nid in nodes):
        return 'other-start'
    if reachable(start, set(nodes)) != set(nodes):
        return 'disconnected'
    if len(nodes) - 1 > earned:
        return 'points'
    return None


MESSAGES = {
    'unknown': 'That skill tree has a node that does not exist. Reload the page and try again.',
    'start': "Your build must include your class's starting node.",
    'other-start': "You can't take another class's starting node.",
    'disconnected': 'Every node must connect back to your starting node.',
    'points': 'That build needs more passive points than you have.',
}


def validate(class_id, allocated, earned):
    """Check a client allocation and return it sorted, or raise ValueError."""
    if (not isinstance(allocated, list) or not 1 <= len(allocated) <= len(NODES) or
            any(not isinstance(nid, str) or len(nid) > 64 for nid in allocated)):
        raise ValueError('Send the allocated node ids as a list.')
    if len(set(allocated)) != len(allocated):
        raise ValueError('Each node can be allocated once.')
    reason = problem(class_id, allocated, earned)
    if reason:
        raise ValueError(MESSAGES[reason])
    return sorted(allocated)


def path_to(class_id, allocated, target):
    """The shortest list of new nodes that connects `target` to an allocation, or None."""
    blocked = STARTS - {START_BY_CLASS[class_id]}
    if target in allocated:
        return []
    if target in blocked:
        return None
    previous = {nid: None for nid in allocated}
    queue = deque(allocated)
    while queue:
        current = queue.popleft()
        for nxt in sorted(ADJACENCY[current]):
            if nxt in previous or nxt in blocked:
                continue
            previous[nxt] = current
            if nxt == target:
                path = [nxt]
                while previous[path[-1]] not in allocated:
                    path.append(previous[path[-1]])
                return path[::-1]
            queue.append(nxt)
    return None
