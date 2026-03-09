"""
This module contains all the prompts used by the AI agents in the book writing process.
Each prompt is a template that can be formatted with specific data.
"""

# World building prompt
WORLD_THEME_PROMPT = """
Based on the general topic: {topic}

Create a rich and detailed world setting for a book. Include:
1. Time period and setting
2. Major locations and their descriptions
3. Prominent cultural/historical elements
4. Technology level or magical elements (if applicable)
5. Social/political structures
6. Environment and atmosphere

Be specific and detailed, creating a cohesive world that would support an engaging narrative.
"""

# World suggestions prompt
WORLD_SUGGESTIONS_PROMPT = """
Based on the general topic: {topic}

Create a brief overview of potential world elements for a book. Include:
1. 2-3 potential time periods or settings that would work well
2. 3-5 key elements that would make this world interesting and unique
3. Brief suggestions for the atmosphere and tone 
4. Any potential conflicts or tensions that could exist in this world

This is a preliminary summary to help guide the creation of a more detailed world setting.
Keep it concise but inspiring, focusing on elements that would spark the imagination.
"""

# Character creation prompt
CHARACTER_CREATION_PROMPT = """
Based on the world setting:
{world_theme}

Create {num_characters} distinct characters for a book set in this world. For each character include:
1. Name and role in the story
2. Age and physical description
3. Personality traits and quirks
4. Background/history
5. Motivations and goals
6. Conflicts or challenges they face
7. Relationships with other characters (if applicable)

Make each character complex and three-dimensional, with strengths, flaws, and distinguishing characteristics.
"""

# Outline generation prompt
OUTLINE_GENERATION_PROMPT = """
Based on the world:
{world_theme}

And the characters:
{characters}

Create a detailed {num_chapters}-chapter outline for a book.

For each chapter include:
1. Chapter title
2. Key events and plot developments
3. Character appearances and development
4. Setting/location
5. Major themes or emotional beats
6. Any important revelations or plot twists

Ensure the outline follows a satisfying story structure with a clear beginning, middle, and end.
The plot should build logically with rising action, climax, and resolution.
"""

# Scene generation prompt
SCENE_GENERATION_PROMPT = """
For Chapter {chapter_number}: {chapter_title}

Based on the chapter outline:
{chapter_outline}

And considering:
- World: {world_theme}
- Characters: {relevant_characters}
- Previous chapters: {previous_context}

Generate a detailed scene that includes:
1. Setting description with sensory details
2. Character interactions and dialogue
3. Action and plot advancement
4. Emotional beats and character development
5. Connections to the overall narrative

Write engaging, immersive prose that advances the story while staying true to the established world and characters.
"""

# Chapter generation prompt
CHAPTER_GENERATION_PROMPT = """
Generate Chapter {chapter_number}: {chapter_title}

Based on:
- Chapter outline: {chapter_outline}
- World: {world_theme}
- Characters: {relevant_characters}
- Scenes: {scene_details}
- Previous chapters: {previous_context}

Write a complete chapter that:
1. Follows the outlined plot points
2. Maintains consistent character voices and development
3. Incorporates world-building details naturally
4. Creates engaging prose with a mix of dialogue, action, and description
5. Has proper pacing with rising and falling tension
6. Connects logically to previous and upcoming chapters

The chapter should be at least 5000 words with a clear beginning, middle, and end structure.
"""


# Chapter editing prompt
CHAPTER_EDITING_PROMPT = """
Review and improve the following chapter:

{chapter_content}

Based on:
- Chapter outline: {chapter_outline}
- World: {world_theme}
- Characters: {relevant_characters}
- Previous chapters: {previous_context}

Provide a comprehensive edit that:
1. Improves prose quality and flow
2. Ensures character consistency
3. Enhances descriptive elements
4. Strengthens dialogue and character interactions
5. Maintains continuity with established world and plot
6. Fixes any grammatical or structural issues
7. Ensures the chapter is at least 5000 words

Return the complete edited chapter.
"""


# ============================================================================
# NARRATIVE ENGINE PROMPTS (Phase 1 & 2)
# ============================================================================

# Theme extraction prompt
THEME_EXTRACTION_PROMPT = """
Based on the story premise: {topic}

And the world setting: {world_theme}

Extract and define the core theme of this story.

Please provide:
1. THEME STATEMENT: A one-line statement capturing what the story explores
2. CORE CONFLICT: The central tension that drives the narrative
3. MORAL TENSION: The ethical dilemma or value conflict at the heart of the story
4. THEMATIC TESTS: 2-3 key moments where characters will be tested against this theme

Format your response as:

THEME STATEMENT: [statement]
CORE CONFLICT: [conflict]
MORAL TENSION: [tension]
THEMATIC TESTS:
- [test 1]
- [test 2]
- [test 3]
"""

# Character arc definition prompt
CHARACTER_ARCS_PROMPT = """
Based on these characters:
{characters}

And the story theme: {theme}

Define the arc stages for each character through the story.

For each character, provide:
1. STARTING STATE: Where the character begins psychologically/emotionally
2. ARC STAGES: 4-5 stages of development through the story
3. FINAL STATE: Where the character ends after their transformation
4. KEY MOMENTS: Which scenes/chapters trigger each stage progression

Format as:

CHARACTER: [Name]
STARTING STATE: [description]
ARC STAGES:
  Stage 1 - [name]: [description]
  Stage 2 - [name]: [description]
  Stage 3 - [name]: [description]
  Stage 4 - [name]: [description]
  Stage 5 - [name]: [description]
FINAL STATE: [description]
"""

# Scene chain planning prompt
SCENE_CHAIN_PLANNER_PROMPT = """
Based on the outline:
{outline}

Create a detailed scene chain that breaks down the story into individual causal scenes.

Each scene should follow this structure:
- Goal: What needs to happen in this scene
- Conflict: What opposes the goal
- Outcome: How the scene resolves
- Consequence: What changes as a result
- Next Trigger: What this scene sets up for the next

Generate 20-50 scenes (depending on story complexity) that form a causal chain where each scene directly leads to the next.

CRITICAL: Every scene must change one of these:
- Character knowledge
- Character power/ability
- Character relationships
- Danger level

Format each scene as:

SCENE [number]: [Title]
Goal: [what happens]
Conflict: [what opposes it]
Outcome: [how it resolves]
Consequence: [what changes]
Next Trigger: [what must happen next]
---

Generate all scenes in sequence.
"""

# Scene planner (given current state, plan next scene)
SCENE_PLANNER_PROMPT = """
Based on the current story state:
{story_state}

The outline so far:
{outline}

And the scene chain plan:
{scene_chain_preview}

Plan the next scene to be generated.

Current Progress:
- Completed scenes: {completed_scenes}
- Next scene in chain: Scene {next_scene_number}

Provide:
1. SCENE GOAL: What must happen in this scene
2. CONFLICT: What opposes achieving the goal
3. OUTCOME: How the scene resolves
4. CONSEQUENCE: What changes as a result
5. AFFECTED CHARACTERS: Which characters are impacted
6. CONSTRAINTS: Any plot/character constraints to respect

Format as:

NEXT SCENE: {next_scene_number}
GOAL: [description]
CONFLICT: [description]
OUTCOME: [description]
CONSEQUENCE: [description]
AFFECTED CHARACTERS: [list]
CONSTRAINTS: [list]
"""

# State extraction prompt (after scene generation)
STATE_UPDATE_PROMPT = """
Based on the scene that was just written:

{scene_content}

Extract the story state changes that occurred in this scene.

Identify:
1. CHARACTER CHANGES: How did each character change (status, knowledge, relationships)?
2. ARTIFACT CHANGES: Any changes to magical items, weapons, or key objects?
3. WORLD CHANGES: Any changes to locations, factions, or world state?
4. PLOT PROGRESS: What major plot points or revelations occurred?

Format as:

CHARACTER CHANGES:
- [Character Name]: [status change]
  * [specific development]
  * [specific development]

ARTIFACT CHANGES:
- [Artifact Name]: [status change]
  * Location: [if changed]
  * Owner: [if changed]

WORLD CHANGES:
- [Element]: [status change]
  * [details of change]

PLOT PROGRESS:
- [Major point or revelation]
"""

# Scene generation with state context
SCENE_GENERATION_WITH_STATE_PROMPT = """
Generate a scene for this story.

Scene Specification:
- Goal: {scene_goal}
- Conflict: {scene_conflict}
- Outcome: {scene_outcome}

Story Context:
{story_context}

World: {world_theme}
Characters: {relevant_characters}

Current Story State (what has already happened):
{current_state}

Write an immersive, detailed scene that:
1. Achieves the stated goal
2. Incorporates the specified conflict
3. Resolves with the stated outcome
4. Respects all current story state (characters can't be in two places, dead characters stay dead, etc.)
5. Includes sensory details, dialogue, and character interactions
6. Advances the plot while maintaining consistency
7. Is approximately 2000-3000 words

Write the scene now:
"""


# ============================================================================
# PHASE 1: INITIAL STATE EXTRACTION PROMPTS
# ============================================================================

CHARACTER_INITIAL_STATE_PROMPT = """
Based on these character descriptions:

{characters}

And the story theme:
{theme}

Extract the initial state for each character. For each character provide:

1. NAME: Character's name
2. STATUS: Initial status (e.g., "unaware", "confident", "grieving", "learning")
3. LOCATION: Starting location
4. KNOWLEDGE: What they know at the start
5. RELATIONSHIPS: Initial relationships with other characters
6. INVENTORY/ARTIFACTS: Any items they start with
7. ABILITIES: Skills or powers they possess

Format as JSON:
{{
  "characters": [
    {{
      "name": "Character Name",
      "status": "initial status",
      "location": "starting location",
      "knowledge": ["fact 1", "fact 2"],
      "relationships": {{"Other Character": "relationship type"}},
      "inventory": ["item1", "item2"],
      "abilities": ["ability1", "ability2"]
    }}
  ]
}}

Extract initial state for all characters now:
"""

ARTIFACT_EXTRACTION_PROMPT = """
Based on the world description:

{world_theme}

And the characters:

{characters}

Identify all important artifacts (magical items, weapons, keys, documents, etc.) that exist in the story world.

For each artifact provide:

1. NAME: Artifact name
2. STATUS: Current status (e.g., "hidden", "active", "dormant", "destroyed")
3. LOCATION: Where it currently is
4. OWNER: Who possesses it
5. SIGNIFICANCE: Why it matters to the story
6. PROPERTIES: What it does or what makes it special

Format as JSON:
{{
  "artifacts": [
    {{
      "name": "Artifact Name",
      "status": "current status",
      "location": "location",
      "owner": "character or 'unowned'",
      "significance": "why it matters",
      "properties": ["property1", "property2"]
    }}
  ]
}}

Extract artifacts now:
"""

WORLD_ELEMENTS_EXTRACTION_PROMPT = """
Based on the world setting:

{world_theme}

And the story outline:

{outline}

Identify all major world elements (locations, factions, institutions, natural features, etc.) that define the story world.

For each element provide:

1. NAME: Element name
2. TYPE: Type of element (location, faction, institution, natural_feature, etc.)
3. STATUS: Current status (active, dormant, sealed, destroyed, etc.)
4. DESCRIPTION: Key characteristics
5. INHABITANTS: Who/what exists there
6. SIGNIFICANCE: Why it matters to the story

Format as JSON:
{{
  "world_elements": [
    {{
      "name": "Element Name",
      "type": "element type",
      "status": "current status",
      "description": "key characteristics",
      "inhabitants": ["inhabitant1", "inhabitant2"],
      "significance": "why it matters"
    }}
  ]
}}

Extract world elements now:
"""

THEME_EXTRACTION_PROMPT_DETAILED = """
Based on the story outline:

{outline}

Extract the core theme and central conflicts of this story.

Provide:

1. THEME_STATEMENT: One sentence capturing the story's main theme
2. CORE_CONFLICT: The central tension that drives the narrative
3. MORAL_TENSION: The ethical dilemma at the heart of the story
4. CHARACTER_CONFLICT: How this theme plays out through character development
5. WORLD_CONFLICT: How this theme manifests in world events/changes

Format as JSON:
{{
  "theme": {{
    "statement": "theme statement",
    "core_conflict": "central tension",
    "moral_tension": "ethical dilemma",
    "character_conflict": "how characters embody this",
    "world_conflict": "how world embodies this"
  }}
}}

Extract theme now:
"""

CHARACTER_ARCS_EXTRACTION_PROMPT = """
Based on the outline:

{outline}

And the characters:

{characters}

Define the character arc stages for each main character.

For each character provide:

1. NAME: Character name
2. STARTING_STATE: Psychological/emotional starting point
3. ARC_STAGES: 4-5 development stages through the story
4. FINAL_STATE: Where they end after transformation
5. KEY_MOMENTS: Which chapters trigger each stage

Format as JSON:
{{
  "character_arcs": [
    {{
      "name": "Character Name",
      "starting_state": "initial state description",
      "arc_stages": [
        "Stage 1: description",
        "Stage 2: description",
        "Stage 3: description",
        "Stage 4: description"
      ],
      "final_state": "final state after transformation",
      "key_moments": [
        {{"stage": 1, "chapter": "X", "event": "description"}},
        {{"stage": 2, "chapter": "X", "event": "description"}}
      ]
    }}
  ]
}}

Extract character arcs now:
"""


# ============================================================================
# PHASE 2: PER-CHAPTER SCENE CHAIN GENERATION
# ============================================================================

CHAPTER_SCENE_CHAIN_PROMPT = """
Based on the chapter outline:

{chapter_outline}

And the current story state:

{current_state}

Generate a detailed scene chain for this chapter. Break it down into 4-8 individual scenes.

For each scene provide:

1. SCENE_NUMBER: Sequential number for this chapter (1, 2, 3, etc.)
2. TITLE: Scene title
3. GOAL: What must happen in this scene
4. CONFLICT: What opposes achieving the goal
5. OUTCOME: How the scene resolves
6. CHARACTERS_PRESENT: Which characters appear in this scene
7. PREREQUISITES: What must be true before this scene (character states, artifacts, locations)
8. CONSEQUENCE: What changes as a result of this scene

Format as JSON:
{{
  "chapter": X,
  "scenes": [
    {{
      "scene_number": 1,
      "title": "Scene title",
      "goal": "what must happen",
      "conflict": "what opposes it",
      "outcome": "how it resolves",
      "characters_present": ["Character1", "Character2"],
      "prerequisites": {{
        "character_states": {{"Character1": "status needed"}},
        "artifacts_needed": ["Artifact1"],
        "location": "Location name"
      }},
      "consequence": "what changes"
    }}
  ]
}}

Generate the scene chain now:
"""


# ============================================================================
# PHASE 3: SCENE STATE EXTRACTION AND AUTO-APPLICATION
# ============================================================================

STATE_EXTRACTION_PROMPT = """
Based on the scene that was just generated:

{scene_content}

And the current story state before this scene:

{current_state}

Extract the story state CHANGES that occurred in this scene.

Identify:
1. CHARACTER CHANGES: How did each character change (status, knowledge, relationships)?
2. ARTIFACT CHANGES: Any changes to magical items, weapons, or key objects?
3. WORLD CHANGES: Any changes to locations, factions, or world state?

For each change, specify:
- OLD STATE: What was the state before
- NEW STATE: What is the state now
- EVENT: What in the scene caused this change

Format as JSON:
{{
  "characters": [
    {{
      "name": "Character Name",
      "old_state": {{"status": "old status", "location": "old location"}},
      "new_state": {{"status": "new status", "location": "new location"}},
      "events": ["event1 causing change", "event2 causing change"]
    }}
  ],
  "artifacts": [
    {{
      "name": "Artifact Name",
      "old_state": {{"status": "old", "owner": "old owner"}},
      "new_state": {{"status": "new", "owner": "new owner"}},
      "event": "what happened in the scene"
    }}
  ],
  "world": [
    {{
      "element": "Element Name",
      "old_state": "old state",
      "new_state": "new state",
      "event": "what changed"
    }}
  ]
}}

Extract state changes now (return only valid JSON):
"""


# ============================================================================
# CHAPTER-SPECIFIC STATE GENERATION
# ============================================================================

CHAPTER_INITIAL_STATES_PROMPT = """
You are the Story State Keeper, responsible for tracking all narrative state for chapter {chapter_number}.

Based on the chapter outline:
{chapter_outline}

And the world setting:
{world_theme}

And the characters:
{characters}

{previous_chapter_context}

Generate the INITIAL story state for this chapter. This state reflects:
1. What is true about each character at the START of this chapter
2. What is true about key artifacts
3. What is true about important locations
4. What has already been completed/resolved
5. What conflicts or goals drive this chapter

For each character, specify:
- status: Current emotional/physical/narrative state (e.g., "determined to find the artifact", "recovering from betrayal")
- location: Where they are at chapter start
- relationships: Key relationships and their status
- knowledge: What they know and don't know
- goals: What they want to achieve this chapter

For each artifact:
- status: destroyed, hidden, active, cursed, etc.
- location: Where it is
- owner: Who possesses it (if applicable)
- significance: Why it matters for this chapter

Format as JSON with structure:
{{
  "chapter": {chapter_number},
  "characters": {{
    "Character Name": {{
      "status": "status description",
      "location": "location",
      "relationships": {{"other_character": "relationship status"}},
      "knowledge": ["fact1", "fact2"],
      "goals": ["goal1", "goal2"]
    }}
  }},
  "artifacts": {{
    "Artifact Name": {{
      "status": "status",
      "location": "location",
      "owner": "owner or 'unowned'",
      "significance": "why it matters"
    }}
  }},
  "world": {{
    "current_date": "ISO date",
    "locations": {{
      "Location Name": {{
        "description": "current state",
        "inhabitants": ["char1", "char2"],
        "status": "stable/contested/changed"
      }}
    }},
    "active_conflicts": ["conflict1", "conflict2"],
    "completed_quests": {completed_quests},
    "pending_quests": {pending_quests}
  }},
  "chapter_hook": "The connecting element from previous chapter that launches this chapter"
}}

Generate the chapter initial states now (return only valid JSON):
""" 