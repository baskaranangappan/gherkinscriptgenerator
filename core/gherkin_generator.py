"""
Gherkin Feature Generator
Uses LLMs to generate BDD test scenarios in Gherkin format
Matches expected output format exactly
"""
from typing import List, Dict, Any, Optional
import json
from datetime import datetime
from pathlib import Path
from .llm_provider import BaseLLMProvider, LLMFactory, LLMConfig
from .config import config
from .logger import get_logger

logger = get_logger(__name__)

class GherkinGenerator:
    """Generates Gherkin BDD scenarios using LLMs - Clean, Simple Format"""

    def __init__(self, llm_provider: BaseLLMProvider):
        self.llm = llm_provider
        logger.info(f"Initialized Gherkin generator with {llm_provider.__class__.__name__}")

    def _create_hover_prompt(self, url: str, hover_elements: List[Dict],
                            page_structure: Dict) -> str:
        """Create prompt for hover element test generation"""

        system_context = """You are an expert QA automation engineer. Generate SIMPLE, CLEAN Gherkin scenarios.

        CRITICAL RULES:
        1. NO user stories (As a user, I want...)
        2. NO Background sections
        3. NO data tables
        4. NO technical details (XPath, selectors, classes)
        5. Use "the user" not "I"
        6. Keep scenarios simple and readable
        7. Cover maximum scenarios
        8. Use only: Feature, Scenario, Given, When, Then, And
        9. Each scenario MUST have a UNIQUE, descriptive title that includes the element name
        10. Format: Feature title, BLANK LINE, then scenarios

        Follow the EXACT format shown in examples."""

        # Extract meaningful hover elements info
        hover_info = []
        for elem in hover_elements:  # Limit to top 3
            hover_info.append({
                'text': elem.get('text', '')[:50],
                'revealed': [r.get('text', '')[:30] for r in elem.get('revealed_elements', [])]
            })

        hover_data = json.dumps(hover_info, indent=2)

        prompt = f"""Generate a simple Gherkin feature file for hover interactions on this website:

        URL: {url}
        Page Title: {page_structure.get('title', 'Unknown')}

        Detected Hover Elements (that reveal dropdowns/menus when hovered):
        {hover_data}

        EXPECTED OUTPUT FORMAT (FOLLOW EXACTLY):

        Feature: Validate navigation menu functionality

        Scenario: Verify Store navigation menu dropdown appears on hover
          Given the user is on the "{url}" page
          When the user hovers over the navigation menu "Store"
          Then a dropdown menu should appear
          And the menu should contain clickable options

        Scenario: Verify navigation through Store dropdown menu
          Given the user is on the "{url}" page
          When the user hovers over the navigation menu "Store"
          And clicks the link "Shop the Latest" from the dropdown
          Then the page URL should change to the expected page

        IMPORTANT:
        - BLANK LINE after Feature statement
        - Each Scenario title MUST include the specific element name (e.g., "Store", "Mac")
        - Use ONLY the format above
        - Replace "Store" with actual detected element text
        - Replace "Shop the Latest" with actual revealed element text
        - Keep it simple - no tables, no background, no user stories
        - Use "the user" consistently
        - Hide all technical details
        - Generate maximum unique scenarios with descriptive titles

        Generate the Gherkin feature now:"""

        return prompt, system_context


    def _create_popup_prompt(self, url: str, popup_elements: List[Dict],
                            page_structure: Dict) -> str:
        """Create prompt for popup/modal test generation"""

        system_context = """You are an expert QA automation engineer. Generate SIMPLE, CLEAN Gherkin scenarios.

            CRITICAL RULES:
            1. NO user stories (As a user, I want...)
            2. NO Background sections
            3. NO data tables
            4. NO technical details
            5. Use "the user" not "I"
            6. Keep scenarios simple
            7. Maximum possible scenarios
            8. Follow the exact format provided"""

        # Extract meaningful popup info
        popup_info = []
        for elem in popup_elements:  # Limit to top 3
            popup_details = elem.get('popup_details', [])
            popup_text = popup_details[0].get('text', '')[:150] if popup_details else 'modal content'

            popup_info.append({
                'trigger_text': elem.get('text', '')[:100],
                'popup_content': popup_text
            })

        popup_data = json.dumps(popup_info, indent=2)

        prompt = f"""Generate a simple Gherkin feature file for popup/modal interactions:

                URL: {url}
                Page Title: {page_structure.get('title', 'Unknown')}
                
                Detected Popup Triggers (buttons/links that open modals):
                {popup_data}
                
                EXPECTED OUTPUT FORMAT (FOLLOW EXACTLY):
                
                Feature: Validate "Button Name" pop-up functionality
                
                Scenario: Verify the cancel button in the pop-up
                  Given the user is on the "{url}" page
                  When the user clicks the "Button Name" button
                  Then a pop-up should appear with the title "Popup Title"
                  And the user clicks the "Cancel" button
                  Then the pop-up should close and the user should remain on the same page
                
                Scenario: Verify the continue button in the pop-up
                  Given the user is on the "{url}" page
                  When the user clicks the "Button Name" button
                  Then a pop-up should appear with the title "Popup Title"
                  And the user clicks the "Continue" button
                  Then the page should navigate or perform the expected action
                
                IMPORTANT:
                - Use ONLY the format above
                - Replace "Button Name" with actual detected trigger text
                - Replace "Popup Title" with actual popup content
                - Keep it simple and clean
                - No tables, background, or user stories
                - Use "the user" consistently
                - Test both cancel and continue/confirm actions
                - Generate all the scenarios maximum
                
                Generate the Gherkin feature now:"""

        return prompt, system_context

    def generate_hover_features(self, url: str, hover_elements: List[Dict],
                               page_structure: Dict) -> str:
        """Generate Gherkin features for hover interactions"""
        try:
            logger.info("Generating hover interaction features...")

            if not hover_elements:
                logger.warning("No hover elements found, generating generic feature")
                return self._generate_generic_hover_feature(url)

            prompt, system_prompt = self._create_hover_prompt(url, hover_elements, page_structure)

            feature_content = self.llm.generate(prompt, system_prompt)

            # Clean up the response
            feature_content = self._clean_gherkin_output(feature_content)

            logger.info("Successfully generated hover features")
            return feature_content

        except Exception as e:
            logger.error(f"Error generating hover features: {str(e)}")
            raise

    def generate_popup_features(self, url: str, popup_elements: List[Dict],
                               page_structure: Dict) -> str:
        """Generate Gherkin features for popup interactions"""
        try:
            logger.info("Generating popup interaction features...")

            if not popup_elements:
                logger.warning("No popup elements found, generating generic feature")
                return self._generate_generic_popup_feature(url)

            prompt, system_prompt = self._create_popup_prompt(url, popup_elements, page_structure)

            feature_content = self.llm.generate(prompt, system_prompt)

            # Clean up the response
            feature_content = self._clean_gherkin_output(feature_content)

            logger.info("Successfully generated popup features")
            return feature_content

        except Exception as e:
            logger.error(f"Error generating popup features: {str(e)}")
            raise

    def _clean_gherkin_output(self, content: str) -> str:
        """Clean and format Gherkin output"""
        # Remove markdown code blocks if present
        content = content.replace("```gherkin", "").replace("```", "")

        # Remove any user story sections if LLM added them
        lines = content.split('\n')
        cleaned_lines = []
        skip_until_scenario = False

        for line in lines:
            stripped = line.strip()

            # Skip user story lines
            if stripped.startswith('As a') or stripped.startswith('I want') or stripped.startswith('So that'):
                skip_until_scenario = True
                continue

            # Skip Background sections
            if stripped.startswith('Background:'):
                skip_until_scenario = True
                continue

            # Stop skipping when we hit Feature or Scenario
            if stripped.startswith('Feature:') or stripped.startswith('Scenario:'):
                skip_until_scenario = False

            # Don't skip if not in skip mode
            if not skip_until_scenario and line.strip():
                cleaned_lines.append(line.rstrip())

        # Remove excessive blank lines and add proper spacing after Feature
        final_lines = []
        prev_blank = False
        for i, line in enumerate(cleaned_lines):
            if not line.strip():
                if not prev_blank:
                    final_lines.append(line)
                    prev_blank = True
            else:
                final_lines.append(line)
                prev_blank = False

                # Add blank line after Feature statement
                if line.strip().startswith('Feature:'):
                    final_lines.append('')

        return '\n'.join(final_lines)

    def _generate_generic_hover_feature(self, url: str) -> str:
        """Generate a generic hover feature when no elements detected"""
        return f"""Feature: Validate navigation menu functionality

Scenario: Verify hover reveals dropdown menu
  Given the user is on the "{url}" page
  When the user hovers over a navigation menu item
  Then a dropdown menu should appear
  And the menu should contain clickable options

Scenario: Verify navigation through dropdown menu
  Given the user is on the "{url}" page
  When the user hovers over a navigation menu item
  And clicks a link from the dropdown
  Then the page URL should change to the selected page"""

    def _generate_generic_popup_feature(self, url: str) -> str:
        """Generate a generic popup feature when no elements detected"""
        return f"""Feature: Validate pop-up functionality

Scenario: Verify the cancel button in the pop-up
  Given the user is on the "{url}" page
  When the user clicks a button that triggers a pop-up
  Then a pop-up should appear
  And the user clicks the "Cancel" button
  Then the pop-up should close and the user should remain on the same page

Scenario: Verify the continue button in the pop-up
  Given the user is on the "{url}" page
  When the user clicks a button that triggers a pop-up
  Then a pop-up should appear
  And the user clicks the "Continue" button
  Then the expected action should be performed"""

    def save_feature_file(self, content: str, filename: str) -> Path:
        """Save Gherkin feature to file"""
        try:
            filepath = config.OUTPUTS_DIR / filename
            filepath.write_text(content, encoding='utf-8')
            logger.info(f"Saved feature file: {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Error saving feature file: {str(e)}")
            raise

def create_gherkin_generator(llm_config: LLMConfig) -> GherkinGenerator:
    """Factory function to create Gherkin generator"""
    llm_provider = LLMFactory.create_provider(llm_config)
    return GherkinGenerator(llm_provider)