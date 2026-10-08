export type Rarity='basic'|'common'|'rare'|'epic'|'legendary'
export type Slot='head'|'shoulders'|'back'|'chest'|'hands'|'legs'|'feet'|'mainhand'|'offhand'
export type StatKey='primary'|'stamina'|'crit'|'haste'|'mastery'|'versatility'|'armor'|'damage'
export type PrimaryStat='str'|'agi'|'int'
export type Effect={id:string;name:string;text:string}
export type Item={id:number;slot:Slot;base:string;rarity:Rarity;ilvl:number;name:string;primaryStat:PrimaryStat;twoHand:boolean;stats:Record<StatKey,number>;effect:Effect|null;flavor:string;seed:number;source:string;obtainedAt:string;equipped:boolean}
export type ChestKind='welcome'|'lesson'|'path'|'project'|'reading'|'boss'
export type Chest={source:string;kind:ChestKind;tier:number;tierName:string;title:string;subtitle:string;earnedAt:string|null;opened:boolean;openedAt:string|null;itemIds:number[]}
export type Hero={name:string;race:string;class:string;createdAt:string;level:number;xp:number;levelProgress:number}
export type Stage={stage:number;name:string;boss:string}
/** Enemy strength for the practice arena at a stage already reached. */
export type PracticeStage={stage:number;stageName:string;bossHp:number;enemyHealth:number;enemyDamage:number}
export type Campaign={stage:number;stageName:string;bossName:string;bossHp:number;bossDamage:number;bossRemaining:number;stagesCleared:number;stages:Stage[];targetPower?:number;targetHealth?:number;practice?:PracticeStage[]}
export type BattleOutcome='victory'|'defeat'|'retreat'|'abandoned'
export type BattleSummary={id:number;stage:number;outcome:BattleOutcome;damage:number;kills:number;seconds:number;finishedAt:string}
export type Lifetime={fights:number;victories:number;kills:number;deaths:number;totalDamage:number;bestDamage:number}
export type Battle={id:number;stage:number;stageName:string;bossName:string;bossHp:number;bossDamage:number;bossRemaining:number;targetPower?:number;targetHealth?:number;enemyHealth?:number;enemyDamage?:number}
export type BattleResult={outcome:BattleOutcome;damage:number;stageCleared:boolean;stage:number;chest:Chest|null}
export type GameSummary={enabled:boolean;hero:boolean;unopened:number;battles:number;stage:number}
export type Role='melee'|'ranged'|'caster'
export type ClassInfo={id:string;name:string;armor:'cloth'|'leather'|'mail'|'plate';primary:PrimaryStat;role:Role;color:string;mainhand:string[];offhand:string[]}
export type RaceInfo={id:string;name:string;faction:'alliance'|'horde'|'neutral'}
export type ChestTier={tier:number;name:string;count:string;ilvl:[number,number];floor:Rarity|null;rates:Record<Rarity,number>}
/** Summed passive tree effects by key, for example {power:.06,hp:.03}. backend/game_tree.py lists the keys. */
export type TreeMods=Record<string,number>
export type TreeNodeKind='start'|'small'|'notable'|'keystone'
export type TreeNode={id:string;kind:TreeNodeKind;name:string;sector:string|null;x:number;y:number;mods:TreeMods;text:string[];links:string[];class?:string;small?:string;between?:string[]}
export type TreeSector={id:string;name:string;angle:number;classes:string[];text:string}
export type TreeCatalog={radius:number;nodes:TreeNode[];sectors:TreeSector[]}
/** `refunded` says why a saved allocation no longer applied and was refunded whole. */
export type Passives={allocated:string[];points:{earned:number;spent:number;available:number};refunded:null|'changed'|'points'}
export type Catalog={races:RaceInfo[];classes:ClassInfo[];slots:Slot[];rarities:{id:Rarity;name:string;color:string;index:number}[];chestTiers:ChestTier[];lessonTiers:Record<string,number>;pathTiers:Record<string,number>;effects:Effect[];twoHand:string[];tree:TreeCatalog}
export type GameState={hero:Hero|null;items:Item[];equipment:Partial<Record<Slot,number>>;chests:{unopened:Chest[];opened:Chest[]};luck:{sinceEpic:number;sinceLegendary:number};enabled:boolean;battles:{earned:number;used:number;available:number};campaign:Campaign;lifetime:Lifetime;history:BattleSummary[];passives:Passives|null;catalog:Catalog}
/** What the 3D builders need: enough to draw an item, nothing about stats. */
export type GearLook={slot:Slot;base:string;rarity:Rarity;seed:number;effect:string|null;twoHand:boolean}
