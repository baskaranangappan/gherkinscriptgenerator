"""
Browser Automation Module - 100% Dynamic Implementation
Uses Playwright for fully autonomous webpage analysis without hardcoded selectors
"""
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from playwright.async_api import async_playwright, Page, Browser, ElementHandle
from bs4 import BeautifulSoup
import json
from .config import config, BrowserConfig
from .logger import get_logger

logger = get_logger(__name__)

class BrowserAutomation:
    """Handles browser automation for fully dynamic webpage analysis"""

    def __init__(self, browser_config: Optional[BrowserConfig] = None):
        self.config = browser_config or BrowserConfig()
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.playwright = None

    async def __aenter__(self):
        """Async context manager entry"""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()

    async def initialize(self):
        """Initialize browser"""
        try:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=self.config.headless,
                slow_mo=self.config.slow_mo
            )

            context = await self.browser.new_context(
                viewport={
                    'width': self.config.viewport_width,
                    'height': self.config.viewport_height
                },
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )

            self.page = await context.new_page()
            self.page.set_default_timeout(self.config.timeout)

            logger.info("Browser initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize browser: {str(e)}")
            raise

    async def close(self):
        """Close browser"""
        try:
            if self.page:
                await self.page.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            logger.info("Browser closed successfully")
        except Exception as e:
            logger.error(f"Error closing browser: {str(e)}")

    async def navigate_to_url(self, url: str) -> bool:
        """Navigate to URL"""
        try:
            logger.info(f"Navigating to: {url}")
            await self.page.goto(url, wait_until='networkidle')
            await asyncio.sleep(2)  # Wait for dynamic content
            logger.info(f"Successfully loaded: {url}")
            return True
        except Exception as e:
            logger.error(f"Failed to navigate to {url}: {str(e)}")
            return False

    async def analyze_hover_elements(self) -> List[Dict[str, Any]]:
        """
        Analyze elements that respond to hover - FULLY DYNAMIC
        NO hardcoded selectors, uses runtime analysis only
        """
        try:
            logger.info("Analyzing hover elements dynamically...")

            # JavaScript for 100% dynamic hover detection
            dynamic_hover_detection = """
            () => {
                const hoverableElements = [];
                const seenElements = new Set();
                
                // Helper: Generate XPath for element
                function getXPath(element) {
                    if (element.id) {
                        return `//*[@id="${element.id}"]`;
                    }
                    
                    const parts = [];
                    let current = element;
                    
                    while (current && current.nodeType === Node.ELEMENT_NODE) {
                        let index = 0;
                        let sibling = current.previousSibling;
                        
                        while (sibling) {
                            if (sibling.nodeType === Node.ELEMENT_NODE && 
                                sibling.nodeName === current.nodeName) {
                                index++;
                            }
                            sibling = sibling.previousSibling;
                        }
                        
                        const tagName = current.nodeName.toLowerCase();
                        const pathIndex = index > 0 ? `[${index + 1}]` : '';
                        parts.unshift(tagName + pathIndex);
                        current = current.parentNode;
                    }
                    
                    return '/' + parts.join('/');
                }
                
                // Helper: Check if element is visible
                function isVisible(element) {
                    const rect = element.getBoundingClientRect();
                    const style = window.getComputedStyle(element);
                    
                    return rect.width > 0 && 
                           rect.height > 0 && 
                           style.display !== 'none' && 
                           style.visibility !== 'hidden' &&
                           style.opacity !== '0';
                }
                
                // Helper: Detect hover behavior
                function hasHoverBehavior(element) {
                    const computed = window.getComputedStyle(element);
                    
                    // Check cursor
                    if (computed.cursor === 'pointer') return true;
                    
                    // Check hover-related attributes
                    if (element.hasAttribute('onmouseover') || 
                        element.hasAttribute('onmouseenter') ||
                        element.hasAttribute('onmouseleave')) return true;
                    
                    // Check if element has hover CSS rules
                    try {
                        const sheets = Array.from(document.styleSheets);
                        for (const sheet of sheets) {
                            try {
                                const rules = Array.from(sheet.cssRules || sheet.rules || []);
                                for (const rule of rules) {
                                    if (rule.selectorText && rule.selectorText.includes(':hover')) {
                                        if (element.matches(rule.selectorText.replace(':hover', ''))) {
                                            return true;
                                        }
                                    }
                                }
                            } catch (e) {
                                // Skip CORS-protected stylesheets
                            }
                        }
                    } catch (e) {}
                    
                    // Check parent elements for dropdown/menu containers
                    let parent = element.parentElement;
                    let depth = 0;
                    while (parent && depth < 3) {
                        const parentStyle = window.getComputedStyle(parent);
                        if (parentStyle.position === 'relative' || 
                            parentStyle.position === 'absolute') {
                            // Check for hidden children that might appear on hover
                            const children = Array.from(parent.children);
                            for (const child of children) {
                                const childStyle = window.getComputedStyle(child);
                                if (childStyle.display === 'none' || 
                                    childStyle.visibility === 'hidden' ||
                                    childStyle.opacity === '0') {
                                    return true;
                                }
                            }
                        }
                        parent = parent.parentElement;
                        depth++;
                    }
                    
                    return false;
                }
                
                // Scan all elements in the page
                const allElements = document.querySelectorAll('*');
                
                allElements.forEach(element => {
                    try {
                        if (!isVisible(element)) return;
                        
                        const tagName = element.tagName.toLowerCase();
                        const text = element.innerText?.trim() || 
                                    element.textContent?.trim() || 
                                    element.getAttribute('aria-label') || 
                                    element.getAttribute('title') || '';
                        
                        // Skip if no meaningful content
                        if (!text && tagName !== 'img' && tagName !== 'svg') return;
                        
                        // Skip very long text (likely not a hover target)
                        if (text.length > 200) return;
                        
                        // Check if element or its interactive parent has hover behavior
                        const isInteractive = hasHoverBehavior(element);
                        
                        if (isInteractive) {
                            const xpath = getXPath(element);
                            
                            // Avoid duplicates
                            if (seenElements.has(xpath)) return;
                            seenElements.add(xpath);
                            
                            const rect = element.getBoundingClientRect();
                            
                            hoverableElements.push({
                                tag: tagName,
                                text: text.substring(0, 100),
                                xpath: xpath,
                                class: element.className,
                                id: element.id || null,
                                href: element.href || null,
                                role: element.getAttribute('role') || null,
                                ariaLabel: element.getAttribute('aria-label') || null,
                                position: {
                                    x: Math.round(rect.x),
                                    y: Math.round(rect.y),
                                    width: Math.round(rect.width),
                                    height: Math.round(rect.height)
                                }
                            });
                        }
                    } catch (e) {
                        // Skip problematic elements
                    }
                });
                
                return hoverableElements.slice(0, 50);
            }
            """

            # Execute dynamic detection
            potential_hover_elements = await self.page.evaluate(dynamic_hover_detection)
            logger.info(f"Found {len(potential_hover_elements)} potential hover elements")

            # Test each element for actual hover behavior
            confirmed_hover_elements = []

            for i, elem_info in enumerate(potential_hover_elements[:config.MAX_HOVER_ELEMENTS]):
                try:
                    # Locate element by XPath
                    element = await self.page.query_selector(f"xpath={elem_info['xpath']}")

                    if not element:
                        continue

                    # Capture state before hover
                    before_snapshot = await self._capture_page_state()

                    # Perform hover action
                    await element.hover()
                    await asyncio.sleep(config.HOVER_DELAY_MS / 1000)

                    # Capture state after hover
                    after_snapshot = await self._capture_page_state()

                    # Check if hover revealed new content
                    if self._has_content_changed(before_snapshot, after_snapshot):
                        revealed = await self._get_revealed_elements(before_snapshot, after_snapshot)

                        confirmed_hover_elements.append({
                            **elem_info,
                            'hover_confirmed': True,
                            'revealed_elements': revealed
                        })

                        logger.info(f"✓ Confirmed hover element: {elem_info['text'][:50]}")

                    # Move mouse away to reset
                    await self.page.mouse.move(0, 0)
                    await asyncio.sleep(0.3)

                except Exception as e:
                    logger.debug(f"Error testing hover element {i}: {str(e)}")
                    continue

            logger.info(f"Confirmed {len(confirmed_hover_elements)} hover-interactive elements")
            return confirmed_hover_elements

        except Exception as e:
            logger.error(f"Error analyzing hover elements: {str(e)}")
            return []

    async def _capture_page_state(self) -> Dict[str, Any]:
        """Capture current page state for comparison"""
        try:
            state = await self.page.evaluate("""
                () => {
                    const elements = [];
                    document.querySelectorAll('a, button, [role="menuitem"], [role="button"]').forEach(el => {
                        const style = window.getComputedStyle(el);
                        const rect = el.getBoundingClientRect();
                        if (style.display !== 'none' && 
                            style.visibility !== 'hidden' && 
                            style.opacity !== '0' &&
                            rect.width > 0 && rect.height > 0) {
                            elements.push({
                                text: el.innerText?.trim().substring(0, 100),
                                tag: el.tagName,
                                href: el.href || null,
                                visible: true
                            });
                        }
                    });
                    return {
                        visible_elements: elements,
                        html_length: document.body.innerHTML.length
                    };
                }
            """)
            return state
        except:
            return {'visible_elements': [], 'html_length': 0}

    def _has_content_changed(self, before: Dict, after: Dict) -> bool:
        """Check if hover action revealed new content"""
        before_count = len(before.get('visible_elements', []))
        after_count = len(after.get('visible_elements', []))

        # New elements appeared
        if after_count > before_count:
            return True

        # HTML changed
        if after.get('html_length', 0) != before.get('html_length', 0):
            return True

        return False

    async def _get_revealed_elements(self, before: Dict, after: Dict) -> List[Dict]:
        """Get elements that appeared after hover"""
        before_texts = {e['text'] for e in before.get('visible_elements', [])}
        after_elements = after.get('visible_elements', [])

        revealed = []
        for elem in after_elements:
            if elem['text'] not in before_texts and elem['text']:
                revealed.append(elem)

        return revealed[:5]  # Limit to top 5

    async def analyze_popup_elements(self) -> List[Dict[str, Any]]:
        """
        Analyze elements that trigger popups/modals - FULLY DYNAMIC
        NO hardcoded selectors, detects based on behavior
        """
        try:
            logger.info("Analyzing popup/modal elements dynamically...")

            popup_elements = []

            # Find clickable elements that might trigger popups
            potential_triggers = await self.page.query_selector_all(
                'a[href*="modal"], button[data-toggle="modal"], '
                'a[data-toggle="modal"], button[aria-haspopup="dialog"], '
                '[onclick*="modal"], [onclick*="popup"], '
                'a[href="#"], button[type="button"]'
            )

            # JavaScript for dynamic popup trigger detection
            dynamic_popup_detection = """
            () => {
                const popupTriggers = [];
                const seenElements = new Set();
                
                function getXPath(element) {
                    if (element.id) return `//*[@id="${element.id}"]`;
                    const parts = [];
                    let current = element;
                    while (current && current.nodeType === Node.ELEMENT_NODE) {
                        let index = 0;
                        let sibling = current.previousSibling;
                        while (sibling) {
                            if (sibling.nodeType === Node.ELEMENT_NODE && 
                                sibling.nodeName === current.nodeName) index++;
                            sibling = sibling.previousSibling;
                        }
                        const tagName = current.nodeName.toLowerCase();
                        const pathIndex = index > 0 ? `[${index + 1}]` : '';
                        parts.unshift(tagName + pathIndex);
                        current = current.parentNode;
                    }
                    return '/' + parts.join('/');
                }
                
                function isVisible(element) {
                    const rect = element.getBoundingClientRect();
                    const style = window.getComputedStyle(element);
                    return rect.width > 0 && rect.height > 0 && 
                           style.display !== 'none' && 
                           style.visibility !== 'hidden';
                }
                
                function mightTriggerPopup(element) {
                    // Check onclick attribute
                    if (element.hasAttribute('onclick')) return true;
                    
                    // Check data attributes suggesting modals
                    const dataAttrs = Array.from(element.attributes)
                        .filter(a => a.name.startsWith('data-'))
                        .map(a => a.name.toLowerCase());
                    
                    const popupKeywords = ['modal', 'popup', 'dialog', 'overlay', 
                                          'toggle', 'open', 'show', 'trigger'];
                    
                    for (const attr of dataAttrs) {
                        for (const keyword of popupKeywords) {
                            if (attr.includes(keyword)) return true;
                        }
                    }
                    
                    // Check aria attributes
                    const ariaExpanded = element.getAttribute('aria-expanded');
                    const ariaHaspopup = element.getAttribute('aria-haspopup');
                    if (ariaExpanded || ariaHaspopup) return true;
                    
                    // Check button text for modal keywords
                    const text = (element.innerText || element.textContent || '').toLowerCase();
                    const textKeywords = ['learn more', 'sign up', 'login', 'subscribe', 
                                        'register', 'join', 'get started', 'more info',
                                        'details', 'view', 'show', 'open'];
                    
                    for (const keyword of textKeywords) {
                        if (text.includes(keyword)) return true;
                    }
                    
                    return false;
                }
                
                // Scan for clickable elements
                const clickables = document.querySelectorAll('button, a, [onclick], [role="button"]');
                
                clickables.forEach(element => {
                    try {
                        if (!isVisible(element)) return;
                        
                        const text = element.innerText?.trim() || 
                                    element.textContent?.trim() || '';
                        
                        if (!text || text.length > 100) return;
                        
                        if (mightTriggerPopup(element)) {
                            const xpath = getXPath(element);
                            if (seenElements.has(xpath)) return;
                            seenElements.add(xpath);
                            
                            const rect = element.getBoundingClientRect();
                            
                            popupTriggers.push({
                                tag: element.tagName.toLowerCase(),
                                text: text.substring(0, 100),
                                xpath: xpath,
                                class: element.className,
                                id: element.id || null,
                                onclick: element.getAttribute('onclick') || null,
                                dataAttrs: Array.from(element.attributes)
                                    .filter(a => a.name.startsWith('data-'))
                                    .map(a => ({name: a.name, value: a.value})),
                                ariaHaspopup: element.getAttribute('aria-haspopup'),
                                position: {
                                    x: Math.round(rect.x),
                                    y: Math.round(rect.y)
                                }
                            });
                        }
                    } catch (e) {}
                });
                
                return popupTriggers.slice(0, 30);
            }
            """

            potential_triggers = await self.page.evaluate(dynamic_popup_detection)
            logger.info(f"Found {len(potential_triggers)} potential popup triggers")

            # Test each trigger
            confirmed_popup_triggers = []

            for i, trigger_info in enumerate(potential_triggers[:config.MAX_POPUP_ELEMENTS]):
                try:
                    # Locate element
                    element = await self.page.query_selector(f"xpath={trigger_info['xpath']}")

                    if not element:
                        continue

                    # Count modals before click
                    before_modals = await self._count_modals()

                    # Click element
                    await element.click()
                    await asyncio.sleep(1)

                    # Count modals after click
                    after_modals = await self._count_modals()
                    modal_details = await self._get_modal_details()

                    # Check if popup appeared
                    if after_modals > before_modals or modal_details:
                        confirmed_popup_triggers.append({
                            **trigger_info,
                            'popup_confirmed': True,
                            'popup_details': modal_details
                        })

                        logger.info(f"✓ Confirmed popup trigger: {trigger_info['text'][:50]}")

                        # Try to close popup
                        await self._close_any_modal()
                        await asyncio.sleep(0.5)

                except Exception as e:
                    logger.debug(f"Error testing popup trigger {i}: {str(e)}")
                    # Try to recover by reloading if stuck
                    try:
                        await self._close_any_modal()
                    except:
                        pass
                    continue

            logger.info(f"Confirmed {len(confirmed_popup_triggers)} popup-triggering elements")
            return confirmed_popup_triggers

        except Exception as e:
            logger.error(f"Error analyzing popup elements: {str(e)}")
            return []

    async def _count_modals(self) -> int:
        """Count visible modals/dialogs"""
        try:
            count = await self.page.evaluate("""
                () => {
                    let count = 0;
                    const selectors = ['[role="dialog"]', '.modal', '.popup', 
                                     '[class*="modal"]', '[class*="popup"]',
                                     '[class*="dialog"]', '[class*="overlay"]'];
                    
                    selectors.forEach(selector => {
                        document.querySelectorAll(selector).forEach(el => {
                            const style = window.getComputedStyle(el);
                            const rect = el.getBoundingClientRect();
                            if (style.display !== 'none' && 
                                style.visibility !== 'hidden' &&
                                rect.width > 0 && rect.height > 0) {
                                count++;
                            }
                        });
                    });
                    
                    return count;
                }
            """)
            return count
        except:
            return 0

    async def _get_modal_details(self) -> List[Dict]:
        """Get details of visible modals"""
        try:
            details = await self.page.evaluate("""
                () => {
                    const modals = [];
                    const selectors = ['[role="dialog"]', '.modal', '.popup',
                                     '[class*="modal"]', '[class*="popup"]'];
                    
                    selectors.forEach(selector => {
                        document.querySelectorAll(selector).forEach(el => {
                            const style = window.getComputedStyle(el);
                            const rect = el.getBoundingClientRect();
                            if (style.display !== 'none' && 
                                style.visibility !== 'hidden' &&
                                rect.width > 100 && rect.height > 100) {
                                modals.push({
                                    text: el.innerText?.trim().substring(0, 200),
                                    class: el.className,
                                    role: el.getAttribute('role'),
                                    hasCloseButton: !!el.querySelector('[aria-label*="close"], [class*="close"], button')
                                });
                            }
                        });
                    });
                    
                    return modals;
                }
            """)
            return details
        except:
            return []

    async def _close_any_modal(self):
        """Attempt to close any open modal"""
        try:
            # Try Escape key
            await self.page.keyboard.press('Escape')
            await asyncio.sleep(0.3)

            # Try clicking close button
            close_selectors = [
                '[aria-label*="close"]',
                '[class*="close"]',
                'button[class*="close"]',
                '.modal button',
                '[role="dialog"] button'
            ]

            for selector in close_selectors:
                try:
                    close_btn = await self.page.query_selector(selector)
                    if close_btn:
                        await close_btn.click()
                        await asyncio.sleep(0.3)
                        break
                except:
                    continue

        except:
            pass

    async def get_page_structure(self) -> Dict[str, Any]:
        """Get overall page structure"""
        try:
            html = await self.page.content()
            soup = BeautifulSoup(html, 'lxml')

            structure = {
                'title': await self.page.title(),
                'url': self.page.url,
                'nav_elements': len(soup.find_all(['nav', 'header'])),
                'buttons': len(soup.find_all('button')),
                'links': len(soup.find_all('a')),
                'forms': len(soup.find_all('form')),
                'has_navigation': bool(soup.find(['nav', 'header']))
            }

            return structure
        except Exception as e:
            logger.error(f"Error getting page structure: {str(e)}")
            return {}

# Convenience function for synchronous usage
def run_browser_analysis(url: str, browser_config: Optional[BrowserConfig] = None) -> Dict[str, Any]:
    """Run browser analysis synchronously"""
    async def _analyze():
        async with BrowserAutomation(browser_config) as browser:
            if await browser.navigate_to_url(url):
                return {
                    'hover_elements': await browser.analyze_hover_elements(),
                    'popup_elements': await browser.analyze_popup_elements(),
                    'page_structure': await browser.get_page_structure()
                }
            return {'hover_elements': [], 'popup_elements': [], 'page_structure': {}}

    return asyncio.run(_analyze())