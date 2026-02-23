"""UI Crawler for extracting test data schema from web pages."""
import logging
from typing import Dict, List, Any
import re
from urllib.parse import urlparse, urljoin
try:
    from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeout
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    
logger = logging.getLogger(__name__)


class TestCaseCrawler:
    """Crawls test case URLs to extract schema information dynamically."""
    
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None
        
    def __enter__(self):
        if not PLAYWRIGHT_AVAILABLE:
            logger.warning("Playwright not available. Install with: pip install playwright && playwright install")
            return self
        try:
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(headless=True)
            self.context = self.browser.new_context()
        except Exception as e:
            logger.error(f"Failed to initialize browser: {e}")
        return self
        
    def __exit__(self, *args):
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
            
    def crawl_test_cases(self, urls: List[str], scenario_hints: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Crawl multiple test case URLs and extract schema information.
        
        Args:
            urls: List of URLs to crawl (test cases)
            scenario_hints: Optional hints about the domain/scenario
            
        Returns:
            Dict with entities, fields, and inferred schema
        """
        if not PLAYWRIGHT_AVAILABLE:
            logger.warning("Playwright not available, returning empty schema")
            return self._fallback_schema(scenario_hints)
            
        extracted_schemas = []
        for url in urls:
            try:
                schema = self._crawl_single_page(url, scenario_hints)
                if schema:
                    extracted_schemas.append(schema)
            except Exception as e:
                logger.error(f"Failed to crawl {url}: {e}")
                
        # Merge all schemas
        return self._merge_schemas(extracted_schemas, scenario_hints)
        
    def _crawl_single_page(self, url: str, scenario_hints: Dict = None) -> Dict:
        """Crawl a single page and extract schema from forms, tables, and UI elements."""
        if not self.context:
            return {}
            
        page = self.context.new_page()
        schema = {
            "url": url,
            "forms": [],
            "tables": [],
            "fields": []
        }
        
        try:
            page.goto(url, timeout=30000)
            page.wait_for_load_state("networkidle", timeout=10000)
            
            # Phase 1: Extract from forms
            forms = page.query_selector_all("form")
            for form in forms:
                form_schema = self._extract_form_schema(form, page)
                if form_schema:
                    schema["forms"].append(form_schema)
                    
            # Phase 2: Extract from tables
            tables = page.query_selector_all("table")
            for table in tables:
                table_schema = self._extract_table_schema(table)
                if table_schema:
                    schema["tables"].append(table_schema)
                    
            # Phase 3: Extract from other UI elements (inputs, selects not in forms)
            orphan_inputs = page.query_selector_all("input:not(form input), select:not(form select), textarea:not(form textarea)")
            orphan_fields = []
            for inp in orphan_inputs:
                field = self._extract_field_info(inp)
                if field:
                    orphan_fields.append(field)
            if orphan_fields:
                schema["forms"].append({"name": "orphan_fields", "fields": orphan_fields})
                
        except Exception as e:
            logger.error(f"Error crawling {url}: {e}")
        finally:
            page.close()
            
        return schema
        
    def _extract_form_schema(self, form, page: Page) -> Dict:
        """Extract schema from a form element."""
        form_name = form.get_attribute("name") or form.get_attribute("id") or form.get_attribute("class") or "unnamed_form"
        action = form.get_attribute("action") or ""
        
        fields = []
        inputs = form.query_selector_all("input, select, textarea")
        
        for inp in inputs:
            field = self._extract_field_info(inp)
            if field:
                fields.append(field)
                
        return {
            "name": form_name,
            "action": action,
            "fields": fields
        } if fields else None
        
    def _extract_field_info(self, element) -> Dict:
        """Extract field information from an input element."""
        tag_name = element.evaluate("el => el.tagName").lower()
        field_type = element.get_attribute("type") or "text"
        name = element.get_attribute("name") or element.get_attribute("id") or element.get_attribute("placeholder") or ""
        
        if not name or name in ["submit", "button", "csrf", "token"]:
            return None
            
        # Infer data type
        inferred_type = self._infer_field_type(name, field_type, element)
        
        field = {
            "name": name,
            "tag": tag_name,
            "type": field_type,
            "inferred_type": inferred_type,
            "placeholder": element.get_attribute("placeholder") or "",
            "required": element.get_attribute("required") is not None,
            "pattern": element.get_attribute("pattern") or ""
        }
        
        # For select, get options
        if tag_name == "select":
            options = element.query_selector_all("option")
            field["options"] = [opt.inner_text() for opt in options[:10]]  # Limit to 10
            
        return field
        
    def _extract_table_schema(self, table) -> Dict:
        """Extract schema from an HTML table."""
        headers = []
        thead = table.query_selector("thead")
        if thead:
            ths = thead.query_selector_all("th")
            headers = [th.inner_text().strip() for th in ths]
        else:
            # Try first tr
            first_row = table.query_selector("tr")
            if first_row:
                ths = first_row.query_selector_all("th, td")
                headers = [th.inner_text().strip() for th in ths]
                
        if not headers:
            return None
            
        # Sample a few rows to infer types
        rows = table.query_selector_all("tbody tr")[:5]
        sample_data = []
        for row in rows:
            cells = row.query_selector_all("td")
            sample_data.append([cell.inner_text().strip() for cell in cells])
            
        columns = []
        for i, header in enumerate(headers):
            if not header:
                continue
            values = [row[i] for row in sample_data if i < len(row)]
            inferred_type = self._infer_type_from_values(values)
            columns.append({
                "name": header,
                "inferred_type": inferred_type
            })
            
        return {
            "name": "table_" + str(id(table))[:8],
            "columns": columns
        } if columns else None
        
    def _infer_field_type(self, name: str, field_type: str, element) -> str:
        """Infer the semantic type of a field."""
        name_lower = name.lower()
        
        # Email
        if field_type == "email" or "email" in name_lower or "mail" in name_lower:
            return "email"
        # Phone
        if field_type == "tel" or "phone" in name_lower or "mobile" in name_lower:
            return "phone"
        # Date
        if field_type == "date" or "date" in name_lower or "dob" in name_lower or "birth" in name_lower:
            return "date"
        # Number
        if field_type == "number" or any(x in name_lower for x in ["age", "price", "amount", "quantity", "count"]):
            return "integer"
        # Name
        if any(x in name_lower for x in ["name", "first", "last", "fullname"]):
            return "person_name"
        # Address
        if any(x in name_lower for x in ["address", "street", "city", "zip", "postal"]):
            return "address"
        # Password
        if field_type == "password" or "password" in name_lower or "pwd" in name_lower:
            return "password"
        # Boolean
        if field_type == "checkbox":
            return "boolean"
            
        return "string"
        
    def _infer_type_from_values(self, values: List[str]) -> str:
        """Infer type from sample values."""
        if not values:
            return "string"
            
        # Check if all numeric
        numeric_count = sum(1 for v in values if v.replace(".", "", 1).replace("-", "", 1).isdigit())
        if numeric_count == len(values):
            return "number"
            
        # Check for dates
        date_pattern = re.compile(r'\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}')
        date_count = sum(1 for v in values if date_pattern.search(v))
        if date_count > len(values) * 0.5:
            return "date"
            
        # Check for emails
        email_pattern = re.compile(r'[\w\.-]+@[\w\.-]+\.\w+')
        email_count = sum(1 for v in values if email_pattern.search(v))
        if email_count > len(values) * 0.5:
            return "email"
            
        return "string"
        
    def _merge_schemas(self, schemas: List[Dict], scenario_hints: Dict = None) -> Dict:
        """Merge multiple page schemas into a unified schema."""
        if not schemas:
            return self._fallback_schema(scenario_hints)
            
        merged = {
            "entities": {},
            "domain": scenario_hints.get("domain", "generic") if scenario_hints else "generic",
            "scenario": scenario_hints.get("scenario", "default") if scenario_hints else "default"
        }
        
        # Collect all forms and tables
        all_forms = []
        all_tables = []
        for schema in schemas:
            all_forms.extend(schema.get("forms", []))
            all_tables.extend(schema.get("tables", []))
            
        # Convert forms to entities
        for form in all_forms:
            entity_name = self._normalize_entity_name(form["name"])
            if entity_name not in merged["entities"]:
                merged["entities"][entity_name] = {"fields": {}, "source": "form"}
                
            for field in form.get("fields", []):
                field_name = self._normalize_field_name(field["name"])
                if field_name not in merged["entities"][entity_name]["fields"]:
                    merged["entities"][entity_name]["fields"][field_name] = {
                        "type": field["inferred_type"],
                        "required": field.get("required", False)
                    }
                    
        # Convert tables to entities
        for table in all_tables:
            entity_name = self._normalize_entity_name(table["name"])
            if entity_name not in merged["entities"]:
                merged["entities"][entity_name] = {"fields": {}, "source": "table"}
                
            for column in table.get("columns", []):
                field_name = self._normalize_field_name(column["name"])
                if field_name not in merged["entities"][entity_name]["fields"]:
                    merged["entities"][entity_name]["fields"][field_name] = {
                        "type": column["inferred_type"],
                        "required": False
                    }
                    
        return merged
        
    def _normalize_entity_name(self, name: str) -> str:
        """Normalize entity name to a consistent format."""
        # Remove special chars, convert to snake_case
        name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
        name = re.sub(r'_+', '_', name).strip('_')
        return name.lower() or "entity"
        
    def _normalize_field_name(self, name: str) -> str:
        """Normalize field name to a consistent format."""
        name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
        name = re.sub(r'_+', '_', name).strip('_')
        return name.lower() or "field"
        
    def _fallback_schema(self, scenario_hints: Dict = None) -> Dict:
        """Provide a fallback schema when crawling is not available."""
        domain = scenario_hints.get("domain", "generic") if scenario_hints else "generic"
        
        # Basic schemas for common domains
        if domain == "ecommerce":
            return {
                "entities": {
                    "customer": {
                        "fields": {
                            "id": {"type": "integer", "required": True},
                            "email": {"type": "email", "required": True},
                            "name": {"type": "person_name", "required": True},
                            "phone": {"type": "phone", "required": False},
                            "address": {"type": "address", "required": False}
                        },
                        "source": "default"
                    },
                    "order": {
                        "fields": {
                            "id": {"type": "integer", "required": True},
                            "customer_id": {"type": "integer", "required": True},
                            "order_date": {"type": "date", "required": True},
                            "total_amount": {"type": "number", "required": True},
                            "status": {"type": "string", "required": True}
                        },
                        "source": "default"
                    }
                },
                "domain": "ecommerce",
                "scenario": "default"
            }
        elif domain == "banking":
            return {
                "entities": {
                    "account": {
                        "fields": {
                            "id": {"type": "integer", "required": True},
                            "account_number": {"type": "string", "required": True},
                            "customer_name": {"type": "person_name", "required": True},
                            "balance": {"type": "number", "required": True},
                            "account_type": {"type": "string", "required": True}
                        },
                        "source": "default"
                    },
                    "transaction": {
                        "fields": {
                            "id": {"type": "integer", "required": True},
                            "account_id": {"type": "integer", "required": True},
                            "amount": {"type": "number", "required": True},
                            "transaction_date": {"type": "date", "required": True},
                            "transaction_type": {"type": "string", "required": True}
                        },
                        "source": "default"
                    }
                },
                "domain": "banking",
                "scenario": "default"
            }
        else:
            # Generic fallback
            return {
                "entities": {
                    "test_entity": {
                        "fields": {
                            "id": {"type": "integer", "required": True},
                            "name": {"type": "string", "required": True},
                            "created_at": {"type": "date", "required": True}
                        },
                        "source": "default"
                    }
                },
                "domain": "generic",
                "scenario": "default"
            }
