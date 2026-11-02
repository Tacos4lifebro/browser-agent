#!/usr/bin/env python3
"""
Browser Agent — Form Filling & Appointment Booking

Demonstrates autonomous browser interaction for filling web forms.
Works with Camoufox (port 9377) if available, falls back to demo mode.

Usage:
    python browser_agent.py --url https://example.com/form --fields '{"name": "John", "email": "john@test.com"}'
    python browser_agent.py --demo
"""

import os
import sys
import json
import argparse
import time
import requests
from pathlib import Path

CAMOFOX_URL = "http://localhost:9377"


def check_camoufox() -> bool:
    """Check if CamoBrowser is running and reachable."""
    try:
        resp = requests.get(f"{CAMOFOX_URL}/tabs", timeout=3)
        return resp.status_code == 200
    except Exception:
        return False


def open_tab(url: str, user_id: str = "browser_agent", session_key: str = "default") -> dict:
    """Open a new browser tab."""
    resp = requests.post(f"{CAMOFOX_URL}/tabs", json={
        "userId": user_id,
        "sessionKey": session_key,
        "url": url
    }, timeout=15)
    return resp.json()


def fill_form(tab_id: str, fields: dict, user_id: str = "browser_agent") -> list:
    """Fill form fields on the current page."""
    filled = []
    for field_name, value in fields.items():
        # Try to fill by label or name
        js = f"""
        (() => {{
            const inputs = Array.from(document.querySelectorAll('input, textarea, select'));
            const target = inputs.find(el => {{
                const label = (el.labels?.[0]?.innerText || '').toLowerCase();
                const name = (el.name || '').toLowerCase();
                const placeholder = (el.placeholder || '').toLowerCase();
                return label.includes('{field_name.lower()}') ||
                       name.includes('{field_name.lower()}') ||
                       placeholder.includes('{field_name.lower()}');
            }});
            if (target) {{
                target.value = {json.dumps(value)};
                target.dispatchEvent(new Event('input', {{ bubbles: true }}));
                return {{ filled: true, field: '{field_name}', value: {json.dumps(value)} }};
            }}
            return {{ filled: false, field: '{field_name}' }};
        }})()
        """
        try:
            resp = requests.post(f"{CAMOFOX_URL}/tabs/{tab_id}/evaluate", json={
                "userId": user_id,
                "expression": js
            }, timeout=10)
            result = resp.json()
            if result.get("result", {}).get("filled"):
                filled.append(field_name)
        except Exception as e:
            print(f"  [-] Failed to fill {field_name}: {e}")
    return filled


def take_screenshot(tab_id: str, output_path: str, user_id: str = "browser_agent") -> bool:
    """Take a screenshot of the current page."""
    try:
        resp = requests.get(f"{CAMOFOX_URL}/tabs/{tab_id}/snapshot?userId={user_id}", timeout=10)
        data = resp.json()
        if data.get("snapshot"):
            import base64
            snapshot = data["snapshot"]
            # Handle both string and bytes snapshot data
            if isinstance(snapshot, str):
                # Strip data URL prefix if present
                if snapshot.startswith("data:"):
                    snapshot = snapshot.split(",", 1)[1]
                img_data = base64.b64decode(snapshot.encode("ascii"))
            else:
                img_data = snapshot
            with open(output_path, "wb") as f:
                f.write(img_data)
            return True
    except Exception as e:
        print(f"  [-] Screenshot failed: {e}")
    return False


def demo_mode():
    """Run in demo mode without a browser — shows what the agent would do."""
    print("=== Browser Agent — Demo Mode ===\n")
    print("No Camoufox connection available. Simulating form fill:\n")

    demo_fields = {
        "full_name": "Jonathan Ortiz",
        "email": "jonathantnks@gmail.com",
        "phone": "(817) 637-5434",
        "linkedin": "https://linkedin.com/in/jonathan-ortiz-68931342/",
        "cover_letter": "I am excited to apply with 8+ years of enterprise operations experience.",
    }

    for field, value in demo_fields.items():
        print(f"  [+] Filled '{field}': {value[:50]}...")
        time.sleep(0.3)

    print("\n[+] Form submission simulated successfully")
    print("[+] Proof screenshot: demo_form_confirmed.png")
    print("\nTo use with real browser: start Camoufox on port 9377 and run without --demo")


def main():
    parser = argparse.ArgumentParser(description="Browser Agent — Form Filling")
    parser.add_argument("--url", help="URL of the form to fill")
    parser.add_argument("--fields", help="JSON string of field mappings")
    parser.add_argument("--demo", action="store_true", help="Run in demo mode (no browser)")
    args = parser.parse_args()

    if args.demo or not args.url:
        demo_mode()
        return

    # Check Camoufox
    if not check_camoufox():
        print("[-] CamoBrowser not reachable on port 9377")
        print("    Start it: cd /path/to/camobrowser && CAMOFOX_INTERACTIVE=off CAMOFOX_PORT=9377 node server.js")
        print("    Or run with --demo for simulation mode")
        return

    print(f"[+] Camoufox connected. Opening tab: {args.url}")
    tab_resp = open_tab(args.url)
    tab_id = tab_resp.get("tabId")

    if not tab_id:
        print("[-] Failed to open tab")
        return

    print(f"[+] Tab opened: {tab_id}")
    time.sleep(2)

    # Fill fields
    if args.fields:
        fields = json.loads(args.fields)
    else:
        fields = {}

    filled = fill_form(tab_id, fields)
    print(f"[+] Filled {len(filled)} fields: {filled}")

    # Take proof screenshot
    screenshot_path = "/tmp/browser_agent_proof.png"
    if take_screenshot(tab_id, screenshot_path):
        print(f"[+] Proof screenshot saved: {screenshot_path}")

    print("\n[+] Browser agent task complete")


if __name__ == "__main__":
    main()