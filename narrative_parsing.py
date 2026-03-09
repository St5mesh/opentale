"""
Advanced parsing utilities for extracting structured data from narrative engine responses.

This module provides robust parsing for AI-generated content that follows specific formats.
"""

import re
from typing import Dict, List, Optional, Tuple


class NarrativeParser:
    """Parses structured responses from narrative engine prompts."""
    
    @staticmethod
    def parse_theme_response(response: str) -> Dict[str, str]:
        """Parse theme extraction response with robust extraction.
        
        Handles various formats including markdown formatting.
        Looks for THEME STATEMENT, CORE CONFLICT, MORAL TENSION, and THEMATIC TESTS.
        """
        result = {
            'statement': '',
            'core_conflict': '',
            'moral_tension': '',
            'thematic_tests': []
        }
        
        # Normalize markdown formatting - remove **, ##, etc
        normalized = response.replace('**', '').replace('##', '').replace('_', '')
        
        # Helper to find field value with flexible pattern matching
        def extract_field(text, field_name, next_fields=None):
            """Extract field value, stopping at next field or double newline."""
            if next_fields is None:
                next_fields = []
            
            # Try pattern: "FIELD NAME: value"
            pattern = f"{field_name}\\s*:+\\s*(.+?)(?=\\n(?:{field_name}|{'|'.join(next_fields)}|\\n\\n|$))"
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                # Clean up markdown, bullet points, and extra formatting
                value = re.sub(r'^[*\-\s]+', '', value)
                value = re.sub(r'\n[*\-]\s+', ' ', value)
                return value
            return ''
        
        # Extract each field with fallbacks
        result['statement'] = extract_field(
            normalized, 'THEME\\s+STATEMENT',
            ['CORE\\s+CONFLICT', 'CORE\\s+TENSION', 'STORY\\s+PREMISE']
        )
        
        result['core_conflict'] = extract_field(
            normalized, 'CORE\\s+CONFLICT',
            ['MORAL\\s+TENSION', 'CENTRAL\\s+CONFLICT', 'CONFLICT']
        )
        
        result['moral_tension'] = extract_field(
            normalized, 'MORAL\\s+TENSION',
            ['THEMATIC\\s+TESTS', 'ETHICAL\\s+DILEMMA', 'TESTS']
        )
        
        # Extract thematic tests (list items) - more flexible pattern
        tests_pattern = r'THEMATIC\s+TESTS:?\s*(.+?)(?=\n\n|$)'
        tests_match = re.search(tests_pattern, normalized, re.DOTALL | re.IGNORECASE)
        if tests_match:
            tests_text = tests_match.group(1)
            # Extract all bullet/numbered items
            # Try bullet format first: "- item" or "* item"
            tests = re.findall(r'^[\s]*[-*]\s+(.+?)$', tests_text, re.MULTILINE)
            # Also try numbering format: "1. item"
            if not tests:
                tests = re.findall(r'^[\s]*\d+\.\s+(.+?)$', tests_text, re.MULTILINE)
            # If still nothing, try to extract any line that's indented or starts with common markers
            if not tests:
                tests = re.findall(r'^[\s]{2,}(.+?)$', tests_text, re.MULTILINE)
            # Clean up extracted tests
            result['thematic_tests'] = [
                re.sub(r'^[*\-_\s]+', '', t.strip())
                for t in tests if t.strip() and len(t.strip()) > 5
            ]
        
        # Fallback: if nothing extracted, try to find any substantial content
        if not result['statement'] and 'statement' in normalized.lower():
            match = re.search(r'statement[:\s]+([^.\n]+(?:[.\n][^.\n]*)?)', normalized, re.IGNORECASE)
            if match:
                result['statement'] = match.group(1).strip()
        
        return result
    
    @staticmethod
    def parse_character_arcs_response(response: str) -> Dict[str, List[str]]:
        """Parse character arcs response.
        
        Expected format:
        CHARACTER: [Name]
        STARTING STATE: [text]
        ARC STAGES:
          Stage 1 - [name]: [text]
          Stage 2 - [name]: [text]
        FINAL STATE: [text]
        """
        arcs = {}
        
        # Split by CHARACTER: marker
        char_blocks = re.split(r'^CHARACTER:\s*', response, flags=re.MULTILINE)
        
        for block in char_blocks[1:]:  # Skip first empty split
            lines = block.strip().split('\n')
            if not lines:
                continue
            
            char_name = lines[0].strip()
            arc_stages = []
            
            # Find ARC STAGES section
            in_stages = False
            for line in lines[1:]:
                if 'ARC STAGES' in line:
                    in_stages = True
                elif in_stages and ('FINAL STATE' in line or 'CHARACTER:' in line):
                    in_stages = False
                elif in_stages and ('Stage' in line or line.strip().startswith('-')):
                    # Extract stage description
                    match = re.search(r'Stage\s+\d+\s*[-–]\s*(.+)$', line)
                    if match:
                        stage_text = match.group(1).strip()
                        if ':' in stage_text:
                            stage_name, stage_desc = stage_text.split(':', 1)
                            arc_stages.append(f"{stage_name.strip()}: {stage_desc.strip()}")
                        else:
                            arc_stages.append(stage_text)
                    elif line.strip().startswith('-'):
                        stage_text = line.strip()[1:].strip()
                        if stage_text:
                            arc_stages.append(stage_text)
            
            if arc_stages:
                arcs[char_name] = arc_stages
        
        return arcs
    
    @staticmethod
    def parse_scene_chain_response(response: str) -> List[Dict[str, str]]:
        """Parse scene chain planning response with robust extraction.
        
        Handles various formats including markdown and flexible scene numbering.
        Looks for SCENE [number], Scene [number], etc.
        """
        scenes = []
        
        # Normalize markdown formatting
        normalized = response.replace('**', '').replace('##', '').replace('_', '')
        
        # Try multiple scene marker patterns
        # Pattern 1: "SCENE 1: Title" or "Scene 1: Title"
        scene_blocks = re.split(r'^[\s]*(?:SCENE|Scene)\s*[\#\.]*\s*(\d+)\s*[:.\-]*\s*', normalized, flags=re.MULTILINE | re.IGNORECASE)
        
        if len(scene_blocks) < 2:
            # Pattern 2: "1. Title" or "### Scene 1 Title"
            scene_blocks = re.split(r'^[\s]*(?:\d+[\.\)]\s+|###\s+Scene\s+\d+\s*[:.\-]*\s*)(.+?)$', normalized, flags=re.MULTILINE)
        
        # Process scene blocks
        for i in range(1, len(scene_blocks), 2):
            if i + 1 >= len(scene_blocks):
                continue
            
            try:
                scene_num_str = scene_blocks[i]
                scene_num = int(re.search(r'\d+', scene_num_str).group() if re.search(r'\d+', scene_num_str) else i // 2)
                scene_content = scene_blocks[i + 1] if i + 1 < len(scene_blocks) else ""
            except (ValueError, IndexError, AttributeError):
                continue
            
            # Extract title (first non-empty line)
            lines = scene_content.strip().split('\n')
            title = lines[0].strip() if lines else ""
            if not title or title.startswith('Goal:') or title.startswith('Conflict:'):
                title = f"Scene {scene_num}"
            
            scene_dict = {
                'scene_number': scene_num,
                'title': title,
                'goal': '',
                'conflict': '',
                'outcome': '',
                'consequence': '',
                'next_trigger': ''
            }
            
            # Extract fields with flexible patterns
            content_text = '\n'.join(lines[1:]) if len(lines) > 1 else scene_content
            
            # Helper to extract field value
            def extract_scene_field(text, field_name):
                """Extract field value with flexible patterns."""
                patterns = [
                    rf'^[\s]*{field_name}\s*:\s*(.+?)(?=\n[\s]*(?:Goal|Conflict|Outcome|Consequence|Next|---)|$)',
                    rf'{field_name}\s*:\s*(.+?)(?=\n[\s]*(?:Goal|Conflict|Outcome|Consequence|Next|---)|$)',
                    rf'\*{field_name}\*\s*:\s*(.+?)(?=\n[\s]*\*|$)',
                ]
                for pattern in patterns:
                    match = re.search(pattern, text, re.MULTILINE | re.DOTALL | re.IGNORECASE)
                    if match:
                        value = match.group(1).strip()
                        # Clean markdown
                        value = re.sub(r'^\*+', '', value).strip()
                        value = re.sub(r'\*+$', '', value).strip()
                        return value
                return ''
            
            for field in ['goal', 'conflict', 'outcome', 'consequence']:
                scene_dict[field] = extract_scene_field(content_text, field)
            
            # Try to extract next trigger/trigger variations
            for trigger_name in ['next_trigger', 'next trigger', 'trigger']:
                value = extract_scene_field(content_text, trigger_name)
                if value:
                    scene_dict['next_trigger'] = value
                    break
            
            # Only add if we found at least one field populated
            if any(scene_dict[k] for k in ['goal', 'conflict', 'outcome', 'consequence', 'next_trigger']):
                scenes.append(scene_dict)
        
        return scenes
    
    @staticmethod
    def parse_state_update_response(response: str) -> Dict[str, any]:
        """Parse state update extraction response.
        
        Expected format:
        CHARACTER CHANGES:
        - [Character]: [change]
          * [detail]
        
        ARTIFACT CHANGES:
        - [Artifact]: [change]
          * [detail]
        
        WORLD CHANGES:
        - [Element]: [change]
        
        PLOT PROGRESS:
        - [point]
        """
        result = {
            'character_changes': {},
            'artifact_changes': {},
            'world_changes': {},
            'plot_progress': []
        }
        
        # Extract CHARACTER CHANGES
        match = re.search(
            r'CHARACTER\s+CHANGES:\s*(.+?)(?=\n[A-Z]+\s+CHANGES:|PLOT|$)',
            response, re.MULTILINE | re.DOTALL
        )
        if match:
            result['character_changes'] = NarrativeParser._parse_entity_changes(match.group(1))
        
        # Extract ARTIFACT CHANGES
        match = re.search(
            r'ARTIFACT\s+CHANGES:\s*(.+?)(?=\n[A-Z]+\s+CHANGES:|PLOT|$)',
            response, re.MULTILINE | re.DOTALL
        )
        if match:
            result['artifact_changes'] = NarrativeParser._parse_entity_changes(match.group(1))
        
        # Extract WORLD CHANGES
        match = re.search(
            r'WORLD\s+CHANGES:\s*(.+?)(?=\nPLOT|$)',
            response, re.MULTILINE | re.DOTALL
        )
        if match:
            result['world_changes'] = NarrativeParser._parse_entity_changes(match.group(1))
        
        # Extract PLOT PROGRESS
        match = re.search(
            r'PLOT\s+PROGRESS:\s*(.+?)$',
            response, re.MULTILINE | re.DOTALL
        )
        if match:
            progress_text = match.group(1)
            points = re.findall(r'^[-*]\s*(.+)$', progress_text, re.MULTILINE)
            result['plot_progress'] = [p.strip() for p in points]
        
        return result
    
    @staticmethod
    def _parse_entity_changes(text: str) -> Dict[str, any]:
        """Parse entity changes section.
        
        Format:
        - [Entity Name]: [change summary]
          * [detail]
          * [detail]
        """
        entities = {}
        current_entity = None
        
        for line in text.split('\n'):
            line = line.rstrip()
            if not line.strip():
                continue
            
            # Main entity line
            if line.lstrip().startswith('-'):
                line_content = line.lstrip()[1:].strip()
                if ':' in line_content:
                    entity_name, summary = line_content.split(':', 1)
                    current_entity = entity_name.strip()
                    entities[current_entity] = {
                        'summary': summary.strip(),
                        'details': []
                    }
                else:
                    current_entity = line_content
                    entities[current_entity] = {
                        'summary': '',
                        'details': []
                    }
            
            # Detail line
            elif line.lstrip().startswith('*') and current_entity:
                detail = line.lstrip()[1:].strip()
                if current_entity in entities and detail:
                    entities[current_entity]['details'].append(detail)
        
        return entities
    
    @staticmethod
    def parse_next_scene_plan(response: str) -> Dict[str, any]:
        """Parse next scene planning response.
        
        Expected format:
        NEXT SCENE: [number]
        GOAL: [text]
        CONFLICT: [text]
        OUTCOME: [text]
        CONSEQUENCE: [text]
        AFFECTED CHARACTERS: [list]
        CONSTRAINTS: [list]
        """
        result = {
            'scene_number': 0,
            'goal': '',
            'conflict': '',
            'outcome': '',
            'consequence': '',
            'affected_characters': [],
            'constraints': []
        }
        
        # Extract scene number
        match = re.search(r'NEXT\s+SCENE:\s*(\d+)', response)
        if match:
            result['scene_number'] = int(match.group(1))
        
        # Extract individual fields
        for field in ['goal', 'conflict', 'outcome', 'consequence']:
            pattern = rf'^{field.upper()}:\s*(.+?)(?=\n[A-Z]+:|$)'
            match = re.search(pattern, response, re.MULTILINE | re.DOTALL)
            if match:
                result[field] = match.group(1).strip()
        
        # Extract character list
        match = re.search(
            r'AFFECTED\s+CHARACTERS:\s*(.+?)(?=\nCONSTRAINTS:|$)',
            response, re.MULTILINE | re.DOTALL
        )
        if match:
            chars_text = match.group(1)
            chars = re.findall(r'^[-*]\s*(.+)$', chars_text, re.MULTILINE)
            result['affected_characters'] = [c.strip() for c in chars]
        
        # Extract constraints
        match = re.search(
            r'CONSTRAINTS:\s*(.+?)$',
            response, re.MULTILINE | re.DOTALL
        )
        if match:
            constraints_text = match.group(1)
            constraints = re.findall(r'^[-*]\s*(.+)$', constraints_text, re.MULTILINE)
            result['constraints'] = [c.strip() for c in constraints]
        
        return result
