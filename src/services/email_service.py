import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List
import configparser
import os

from src.models.base_entry import Entry
from src.utils.date_helpers import format_date


class EmailService:
    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                "config.ini"
            )
        self.config_path = config_path
        self._load_config()

    def _load_config(self):
        config = configparser.ConfigParser()
        config.read(self.config_path, encoding="utf-8")
        smtp = config["SMTP"] if "SMTP" in config else {}
        self.enabled = smtp.get("enabled", "false").lower() == "true"
        self.server = smtp.get("server", "")
        self.port = int(smtp.get("port", "587"))
        self.use_tls = smtp.get("use_tls", "true").lower() == "true"
        self.username = smtp.get("username", "")
        self.password = smtp.get("password", "")
        self.from_address = smtp.get("from_address", "")
        self.to_address = smtp.get("to_address", "")

    def save_config(self, server, port, use_tls, username, password, from_addr, to_addr, enabled):
        config = configparser.ConfigParser()
        config.read(self.config_path, encoding="utf-8")
        if "SMTP" not in config:
            config["SMTP"] = {}
        config["SMTP"]["enabled"] = str(enabled).lower()
        config["SMTP"]["server"] = server
        config["SMTP"]["port"] = str(port)
        config["SMTP"]["use_tls"] = str(use_tls).lower()
        config["SMTP"]["username"] = username
        config["SMTP"]["password"] = password
        config["SMTP"]["from_address"] = from_addr
        config["SMTP"]["to_address"] = to_addr
        with open(self.config_path, "w", encoding="utf-8") as f:
            config.write(f)
        self._load_config()

    def send_reminder(self, overdue: List[Entry], due_soon: List[Entry]) -> str:
        if not self.enabled:
            return "E-Mail-Versand ist deaktiviert."
        if not overdue and not due_soon:
            return "Keine fälligen Einträge."

        body = self._build_body(overdue, due_soon)
        msg = MIMEMultipart()
        msg["From"] = self.from_address
        msg["To"] = self.to_address
        msg["Subject"] = "WKZ & Bonus Tracker - Fälligkeitserinnerung"
        msg.attach(MIMEText(body, "plain", "utf-8"))

        try:
            if self.use_tls:
                server = smtplib.SMTP(self.server, self.port)
                server.starttls()
            else:
                server = smtplib.SMTP(self.server, self.port)
            if self.username:
                server.login(self.username, self.password)
            server.send_message(msg)
            server.quit()
            return "E-Mail erfolgreich gesendet."
        except Exception as ex:
            return f"Fehler beim E-Mail-Versand: {ex}"

    def send_test(self) -> str:
        if not self.server:
            return "Kein SMTP-Server konfiguriert."
        msg = MIMEText("Dies ist eine Test-E-Mail vom WKZ & Bonus Tracker.", "plain", "utf-8")
        msg["From"] = self.from_address
        msg["To"] = self.to_address
        msg["Subject"] = "WKZ Tracker - Test"
        try:
            if self.use_tls:
                server = smtplib.SMTP(self.server, self.port)
                server.starttls()
            else:
                server = smtplib.SMTP(self.server, self.port)
            if self.username:
                server.login(self.username, self.password)
            server.send_message(msg)
            server.quit()
            return "Test-E-Mail erfolgreich gesendet."
        except Exception as ex:
            return f"Fehler: {ex}"

    def _build_body(self, overdue: List[Entry], due_soon: List[Entry]) -> str:
        lines = ["WKZ & Bonus Tracker - Fälligkeitserinnerung\n"]
        if overdue:
            lines.append(f"=== ÜBERFÄLLIG ({len(overdue)}) ===")
            for e in overdue:
                lines.append(f"  - {e.entry_type.value}: {e.supplier_name} - {e.description}")
                lines.append(f"    Frist: {format_date(e.billing_deadline)}, Betrag: {e.amount:.2f}")
            lines.append("")
        if due_soon:
            lines.append(f"=== Bald fällig ({len(due_soon)}) ===")
            for e in due_soon:
                days = e.days_until_deadline()
                lines.append(f"  - {e.entry_type.value}: {e.supplier_name} - {e.description}")
                lines.append(f"    Frist: {format_date(e.billing_deadline)} (noch {days} Tage), Betrag: {e.amount:.2f}")
        return "\n".join(lines)
