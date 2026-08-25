from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode

from app.agent.state import AgentState
from app.agent.tools.search import SearchTool
from app.agent.tools.metadata import MetadataTool
from app.agent.tools.section import create_section_tool
from app.agent.tools.page_search import PageSearchTool
from app.agent.tools.extract import InformationExtractionTool
from app.agent.tools.compare import CompareSectionsTool
from app.agent.tools.summarize import SummarizeSectionTool
from app.agent.tools.verify import EvidenceVerificationTool
from app.agent.tools.reasoning import ReasoningTool
from app.llm.gemini import GeminiProvider


def create_agent_graph(
    parsed_document,
    sections,
    vector_store,
    embedder,
    document_id,
):

    # ---------------------------------------------
    # LLM
    # ---------------------------------------------

    llm = GeminiProvider().get_model()

    # ---------------------------------------------
    # Tools
    # ---------------------------------------------

    search_tool = SearchTool(
        vector_store=vector_store,
        embedder=embedder,
        document_id=document_id,
    ).tool

    metadata_tool = MetadataTool(
        parsed_document=parsed_document,
        sections=sections,
    ).tool

    get_section = create_section_tool(
        sections
    )

    page_search_tool = PageSearchTool(
        vector_store=vector_store,
        embedder=embedder,
        document_id=document_id,
    ).tool

    extract_information_tool = InformationExtractionTool(
        llm=llm
    ).tool

    compare_tool = CompareSectionsTool(
        sections=sections,
        llm=llm,
    ).tool

    summarize_tool = SummarizeSectionTool(
        sections=sections,
        llm=llm,
    ).tool

    verify_tool = EvidenceVerificationTool(
        llm=llm
    ).tool

    reasoning_tool = ReasoningTool().tool

    tools = [
        search_tool,
        metadata_tool,
        get_section,
        page_search_tool,
        extract_information_tool,
        compare_tool,
        summarize_tool,
        verify_tool,
        reasoning_tool,
    ]

    # ---------------------------------------------
    # LLM with tools
    # ---------------------------------------------

    llm_with_tools = llm.bind_tools(tools)

    # ---------------------------------------------
    # Agent Node
    # ---------------------------------------------

    def agent_node(state: AgentState):

        response = llm_with_tools.invoke(
            state["messages"]
        )

        return {
            "messages": [response]
        }

    # ---------------------------------------------
    # Tool Node
    # ---------------------------------------------

    tool_node = ToolNode(tools)

    # ---------------------------------------------
    # Routing
    # ---------------------------------------------

    def should_continue(state: AgentState):

        last_message = state["messages"][-1]

        if last_message.tool_calls:
            return "tools"

        return END

    # ---------------------------------------------
    # Graph
    # ---------------------------------------------

    builder = StateGraph(AgentState)

    builder.add_node(
        "agent",
        agent_node
    )

    builder.add_node(
        "tools",
        tool_node
    )

    builder.add_edge(
        START,
        "agent"
    )

    builder.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            END: END,
        }
    )

    builder.add_edge(
        "tools",
        "agent"
    )

    return builder.compile()