"""
agent_graph.py — CarbonMitra ADK 2.0 Graph Workflow Engine
===========================================================
Implements a Google ADK-style Graph Workflow with:
- Input Validation / Guardrail Node
- Intent Classification Node
- Leaf Nodes: Vision Audit Node, Eco Coach Node, and Block Node
- Gemini 2.5 Flash via modern google-genai SDK
"""

from __future__ import annotations

import os
import re
import json
import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import Any

from google import genai
from google.genai import types as genai_types
from PIL import Image

import mcp_tools as mcp

# ---------------------------------------------------------------------------
# Logging Configuration
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("carbon_mitra.agent_graph")

# ---------------------------------------------------------------------------
# Gemini Client Factory
# ---------------------------------------------------------------------------
def get_gemini_client() -> genai.Client:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "GEMINI_API_KEY environment variable is not set. "
            "Please check your .env file or system environment."
        )
    return genai.Client(api_key=api_key)

MODEL_ID = "gemini-2.5-flash"

# ---------------------------------------------------------------------------
# Graph State definition
# ---------------------------------------------------------------------------
class Intent(str, Enum):
    SCAN = "scan"
    CHAT = "chat"
    REDUCE = "reduce"
    OFF_TOPIC = "off_topic"
    UNKNOWN = "unknown"

@dataclass
class GraphState:
    """State variable passed between nodes in the graph."""
    user_message: str = ""
    image_bytes: bytes | None = None
    image_mime_type: str = "image/jpeg"
    chat_history: list[dict[str, str]] = field(default_factory=list)
    intent: Intent = Intent.UNKNOWN
    guard_passed: bool = False
    final_response: str = ""
    extracted_data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

# ---------------------------------------------------------------------------
# Node Definitions
# ---------------------------------------------------------------------------
class Node:
    """Base class for all workflow graph nodes."""
    name: str = "base_node"

    def run(self, state: GraphState, client: genai.Client) -> GraphState:
        raise NotImplementedError


class GuardNode(Node):
    """
    Guardrail Node: Inspects input to prevent prompt injection or off-topic queries.
    Blocks queries unrelated to environment, carbon, climate, sustainability, or bills.
    """
    name = "guard_node"

    ENVIRONMENTAL_KEYWORDS = {
        "carbon", "co2", "emission", "footprint", "climate", "greenhouse",
        "sustainability", "eco", "environment", "pollution", "energy",
        "transport", "electricity", "food", "diet", "recycle", "waste",
        "green", "fossil", "fuel", "solar", "wind", "renewable", "tree",
        "deforestation", "methane", "global warming", "planet", "nature",
        "bill", "receipt", "grocery", "commute", "drive", "flight", "train",
        "bus", "metro", "cycle", "walk", "plant", "vegan", "vegetarian",
        "kwh", "unit", "km", "miles", "litre", "liter", "kg", "tonne",
        "offset", "neutral", "net zero", "ipcc", "cop", "mitra",
        "कार्बन", "उत्सर्जन", "पर्यावरण", "ऊर्जा", "बिजली", "प्रदूषण",
        "जलवायु", "हरित", "पुनर्चक्रण", "टिकाऊ", "प्रकृति", "पेड़",
        "यात्रा", "भोजन", "चुनौती", "अपशिष्ट", "बचाव", "सॉलर", "वायु"
    }

    def _is_safe(self, text: str) -> bool:
        # If there are image bytes, we assume it's a bill/receipt upload -> Safe.
        lower_text = text.lower()
        
        # Check if contains environmental keywords
        for keyword in self.ENVIRONMENTAL_KEYWORDS:
            if keyword in lower_text:
                return True
        return False

    def run(self, state: GraphState, client: genai.Client) -> GraphState:
        if state.image_bytes is not None:
            state.guard_passed = True
            return state

        if self._is_safe(state.user_message):
            state.guard_passed = True
        else:
            state.guard_passed = False
            # Check if query is likely in Hindi
            hindi_chars = sum(1 for c in state.user_message if "\u0900" <= c <= "\u097f")
            if hindi_chars > 2:
                state.final_response = (
                    "🚨 **असुरक्षित या असंबंधित इनपुट ब्लॉक किया गया**\n\n"
                    "मैं केवल पर्यावरण, कार्बन फुटप्रिंट और स्थिरता से संबंधित प्रश्नों का उत्तर दे सकता हूँ। "
                    "कृपया बिजली, पानी, यात्रा, भोजन, रीसाइक्लिंग या प्रदूषण के संबंध में पूछें।"
                )
            else:
                state.final_response = (
                    "🚨 **Off-Topic Query Blocked**\n\n"
                    "I am CarbonMitra, your climate and sustainability assistant. I only respond to questions "
                    "about carbon footprints, eco-friendly habits, green living, and climate change.\n\n"
                    "Please keep our chat focused on sustainability, energy efficiency, clean transit, or low-carbon diets."
                )
        return state


class IntentClassifierNode(Node):
    """
    Classifies user message intent using Gemini.
    """
    name = "intent_classifier_node"

    SYSTEM_PROMPT = """You are the intent classifier router for CarbonMitra, an eco-sustainability assistant.
Classify the user query into exactly one of these intents:
- scan: User uploaded an image or is asking to extract data from a bill, receipt, or label.
- reduce: User wants suggestions, tips, or guidelines to lower their carbon footprint.
- chat: User is chatting or asking standard questions about sustainability, climate, energy, food, or green living.
- off_topic: User query is not related to environment/sustainability.

Output ONLY the classified intent label as a single word in lowercase (e.g. scan, reduce, chat, off_topic)."""

    def run(self, state: GraphState, client: genai.Client) -> GraphState:
        if state.image_bytes is not None:
            state.intent = Intent.SCAN
            return state

        try:
            response = client.models.generate_content(
                model=MODEL_ID,
                contents=state.user_message,
                config=genai_types.GenerateContentConfig(
                    system_instruction=self.SYSTEM_PROMPT,
                    temperature=0.0,
                    max_output_tokens=10,
                )
            )
            raw = response.text.strip().lower()
            if "scan" in raw:
                state.intent = Intent.SCAN
            elif "reduce" in raw:
                state.intent = Intent.REDUCE
            elif "off_topic" in raw:
                state.intent = Intent.OFF_TOPIC
            else:
                state.intent = Intent.CHAT
        except Exception as e:
            logger.warning(f"Intent classification failed: {e}. Defaulting to chat.")
            state.intent = Intent.CHAT

        return state


class VisionAuditNode(Node):
    """
    Visual Audit Node: Processes images of bills/receipts.
    Extracts consumption data and estimates carbon footprint.
    """
    name = "vision_audit_node"

    SYSTEM_PROMPT = """You are CarbonMitra's Multimodal Vision Auditor. 
Analyze the uploaded image (electricity bill, fuel receipt, or item receipt).

Perform the following steps:
1. Identify the Document Type (Electricity Bill, Grocery Receipt, Petrol/Diesel Receipt, etc.).
2. Extract numerical consumption figures (e.g. kWh units, liters of fuel, items purchased).
3. Compute the Carbon Emissions in kg CO2e using Indian standards:
   - Electricity: 0.82 kg CO2 per kWh (Indian grid average)
   - Petrol: 0.20 kg CO2 per km (assuming average vehicle use) or 2.3 kg CO2 per liter if fuel quantity is explicitly visible.
   - Food/Grocery items: standard lifecycle averages (e.g. 3.2 kg CO2 per kg chicken/meat, 1.1 kg CO2 per kg vegetarian goods).
4. Display a beautifully formatted report:
   - 📄 Document Category
   - 🔍 Key Data Extracted
   - 📊 Carbon Breakdown Table
   - 🌳 Sequestration equivalent (e.g. tree-days required to neutralize)
   - 💡 Top 3 targeted suggestions to reduce impact from this activity.

Always output using clean Markdown, with clear structure, bold headers, and lists. Do not use placeholders."""

    def run(self, state: GraphState, client: genai.Client) -> GraphState:
        if not state.image_bytes:
            state.final_response = "❌ No image found to audit. Please upload an image first."
            return state

        try:
            image_part = genai_types.Part.from_bytes(
                data=state.image_bytes,
                mime_type=state.image_mime_type,
            )
            prompt = state.user_message or "Analyze this bill/receipt and audit its carbon footprint."
            
            response = client.models.generate_content(
                model=MODEL_ID,
                contents=[image_part, prompt],
                config=genai_types.GenerateContentConfig(
                    system_instruction=self.SYSTEM_PROMPT,
                    temperature=0.2,
                    max_output_tokens=1500,
                )
            )
            state.final_response = response.text
            # Store some mock extracted data structure for state tracking
            state.extracted_data = {
                "analyzed": True,
                "summary": "Visual audit complete"
            }
        except Exception as e:
            logger.error(f"VisionAuditNode failed: {e}")
            state.final_response = f"⚠️ Vision analysis error: {str(e)}. Please make sure the file is a clear image."
            state.error = str(e)

        return state


class EcoCoachNode(Node):
    """
    AI Eco-Coach Chatbot Node: Handles conversational lifestyle queries and provides localized eco tips.
    Supports English & Hindi.
    """
    name = "eco_coach_node"

    SYSTEM_PROMPT = """You are CarbonMitra, an empathetic, highly knowledgeable AI Eco-Coach for Indian users.
Your goal is to guide users to track, understand, and reduce their lifestyle emissions (Energy, Transit, Food, Waste).

Guidelines:
1. Provide localized, practical context for India. Use rupees (₹), mention common transport (metro, auto, local buses), and Indian power grids/boards (BESCOM, MSEDCL, TANGEDCO).
2. Answer custom lifestyle queries using the emission factors:
   - Electricity: 0.82 kg CO2/kWh
   - Driving: 0.20 kg CO2/km
   - Vegan meal: 0.6 kg CO2, Vegetarian meal: 1.1 kg CO2, Non-Vegetarian meal: 3.2 kg CO2
3. Keep tone encouraging, constructive, and action-oriented. Suggest low-cost or cost-saving solutions first (like switching off standby appliances or energy efficiency), then premium ones (solar panels, EVs).
4. Always respond in the language the user asked in (English or Hindi).
5. Format your output with clear headers and bullet points. Never use placeholders."""

    def run(self, state: GraphState, client: genai.Client) -> GraphState:
        # Build context from recent history
        messages = []
        for msg in state.chat_history[-6:]:  # include up to 3 turns
            role = "user" if msg["role"] == "user" else "model"
            messages.append(genai_types.Content(
                role=role,
                parts=[genai_types.Part.from_text(text=msg["content"])]
            ))
        
        # Add the current user query
        messages.append(genai_types.Content(
            role="user",
            parts=[genai_types.Part.from_text(text=state.user_message)]
        ))

        try:
            response = client.models.generate_content(
                model=MODEL_ID,
                contents=messages,
                config=genai_types.GenerateContentConfig(
                    system_instruction=self.SYSTEM_PROMPT,
                    temperature=0.5,
                    max_output_tokens=1500,
                )
            )
            state.final_response = response.text
        except Exception as e:
            logger.error(f"EcoCoachNode failed: {e}")
            state.final_response = f"⚠️ Chat processing error: {str(e)}. Please try rephrasing your message."
            state.error = str(e)

        return state


class BlockNode(Node):
    """
    Block Node: Politer backup block for off-topic categorizations that pass the regex GuardNode.
    """
    name = "block_node"

    def run(self, state: GraphState, client: genai.Client) -> GraphState:
        state.final_response = (
            "🚨 **Content Blocked**\n\n"
            "I'm sorry, but I can only answer questions related to environmental sustainability, "
            "carbon footprint calculator, and green living options. Please ask me a question related to these topics."
        )
        return state

# ---------------------------------------------------------------------------
# ADK Graph Router (Node/Edge routing model)
# ---------------------------------------------------------------------------
class CarbonMitraGraph:
    """
    CarbonMitra ADK Graph Router. Manages registering nodes and routing edges dynamically.
    """
    def __init__(self) -> None:
        self.client = get_gemini_client()
        self._nodes: dict[str, Node] = {}
        
        # Register nodes
        self.register(GuardNode())
        self.register(IntentClassifierNode())
        self.register(VisionAuditNode())
        self.register(EcoCoachNode())
        self.register(BlockNode())

    def register(self, node: Node) -> None:
        self._nodes[node.name] = node

    def execute(
        self,
        user_message: str,
        image_bytes: bytes | None = None,
        image_mime_type: str = "image/jpeg",
        chat_history: list[dict[str, str]] | None = None
    ) -> dict[str, Any]:
        """
        Executes the graph. Routes states through guard rails, classifiers, and executors.
        """
        state = GraphState(
            user_message=user_message,
            image_bytes=image_bytes,
            image_mime_type=image_mime_type,
            chat_history=chat_history or []
        )

        # 1. Guard check
        state = self._nodes["guard_node"].run(state, self.client)
        if not state.guard_passed:
            logger.info("Guardrail intercepted query.")
            return self._package_result(state)

        # 2. Intent classifier
        state = self._nodes["intent_classifier_node"].run(state, self.client)
        logger.info(f"Routed intent: {state.intent}")

        # 3. Route based on intent
        if state.intent == Intent.SCAN:
            state = self._nodes["vision_audit_node"].run(state, self.client)
        elif state.intent == Intent.OFF_TOPIC:
            state = self._nodes["block_node"].run(state, self.client)
        else: # REDUCE or CHAT
            state = self._nodes["eco_coach_node"].run(state, self.client)

        return self._package_result(state)

    def _package_result(self, state: GraphState) -> dict[str, Any]:
        return {
            "response": state.final_response,
            "intent": state.intent.value if state.intent else "unknown",
            "extracted_data": state.extracted_data,
            "error": state.error,
        }

# Singleton Instance
_graph_instance: CarbonMitraGraph | None = None

def get_graph() -> CarbonMitraGraph:
    global _graph_instance
    if _graph_instance is None:
        _graph_instance = CarbonMitraGraph()
    return _graph_instance

def reset_graph() -> None:
    global _graph_instance
    _graph_instance = None
