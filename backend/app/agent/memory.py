from langchain_core.messages import HumanMessage, AIMessage


MAX_HISTORY_MESSAGES = 15


def get_recent_messages(messages):
    """
    Return safe conversational memory for the LLM.

    We intentionally remove historical tool-call/tool-response
    messages because Gemini requires function-call turns to remain
    in their original valid sequence.

    We preserve:
        HumanMessage
        AIMessage containing a final response

    We exclude:
        AIMessage with tool_calls
        ToolMessage
    """

    safe_messages = []

    for message in messages:

        # --------------------------------------------------
        # User messages
        # --------------------------------------------------

        if isinstance(message, HumanMessage):

            if message.content:

                safe_messages.append(message)

        # --------------------------------------------------
        # Assistant messages
        # --------------------------------------------------

        elif isinstance(message, AIMessage):

            # Never carry old function calls into memory.
            if getattr(message, "tool_calls", None):
                continue

            if message.content:

                safe_messages.append(message)

    # ------------------------------------------------------
    # Keep only the most recent conversational messages
    # ------------------------------------------------------

    return safe_messages[-MAX_HISTORY_MESSAGES:]