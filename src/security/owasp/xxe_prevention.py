import re
import xml.etree.ElementTree as ET
from typing import Optional
from io import BytesIO


class XXEPrevention:
    DANGEROUS_PATTERNS = [
        r"<!ENTITY",
        r"<!DOCTYPE",
        r"SYSTEM\s+\"",
        r"SYSTEM\s+'",
        r"PUBLIC\s+\"",
        r"PUBLIC\s+'",
        r"<!ELEMENT",
        r"<!ATTLIST",
    ]

    EXTERNAL_ENTITY_PATTERNS = [
        r"SYSTEM\s+[\"']file:",
        r"SYSTEM\s+[\"']http:",
        r"SYSTEM\s+[\"']ftp:",
        r"SYSTEM\s+[\"']javascript:",
        r"SYSTEM\s+[\"']data:",
        r"<!ENTITY\s+\w+\s+SYSTEM",
    ]

    def sanitize_xml(self, xml_string: str) -> str:
        for pattern in self.DANGEROUS_PATTERNS:
            xml_string = re.sub(pattern, "", xml_string, flags=re.IGNORECASE)
        xml_string = re.sub(r"<!--.*?-->", "", xml_string, flags=re.DOTALL)
        xml_string = re.sub(r"<\?.*?\?>", "", xml_string, flags=re.DOTALL)
        return xml_string.strip()

    def validate_xml(self, xml_string: str) -> tuple[bool, list[str]]:
        errors = []
        for pattern in self.DANGEROUS_PATTERNS:
            matches = re.findall(pattern, xml_string, re.IGNORECASE)
            if matches:
                errors.append(f"Dangerous XML pattern detected: {pattern}")
        for pattern in self.EXTERNAL_ENTITY_PATTERNS:
            matches = re.findall(pattern, xml_string, re.IGNORECASE)
            if matches:
                errors.append(f"External entity reference detected: {pattern}")
        try:
            ET.fromstring(xml_string)
        except ET.ParseError as e:
            errors.append(f"XML parse error: {str(e)}")
        return len(errors) == 0, errors

    def disable_external_entities(self, xml_string: str) -> str:
        xml_string = re.sub(
            r"<!ENTITY\s+\w+\s+SYSTEM\s+[\"'][^\"']*[\"']\s*>",
            "",
            xml_string,
            flags=re.IGNORECASE,
        )
        xml_string = re.sub(
            r"<!DOCTYPE[^>]*\s+SYSTEM\s+[\"'][^\"']*[\"']\s*>",
            "<!DOCTYPE []>",
            xml_string,
            flags=re.IGNORECASE,
        )
        return xml_string

    def safe_parse_xml(self, xml_string: str) -> Optional[ET.Element]:
        cleaned = self.disable_external_entities(xml_string)
        cleaned = self.sanitize_xml(cleaned)
        try:
            parser = ET.XMLParser()
            parser.entity = {}
            tree = ET.ElementTree(ET.fromstring(cleaned, parser=parser))
            return tree.getroot()
        except ET.ParseError:
            return None

    def create_safe_parser(self) -> ET.XMLParser:
        parser = ET.XMLParser()
        parser.entity = {}
        return parser

    def strip_processing_instructions(self, xml_string: str) -> str:
        return re.sub(r"<\?.*?\?>", "", xml_string, flags=re.DOTALL).strip()

    def validate_and_sanitize(self, xml_string: str) -> tuple[bool, Optional[str], list[str]]:
        is_valid, errors = self.validate_xml(xml_string)
        if not is_valid:
            return False, None, errors
        sanitized = self.sanitize_xml(xml_string)
        sanitized = self.disable_external_entities(sanitized)
        return True, sanitized, []
