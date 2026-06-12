"""LangGraph graph definition for release generation.

    START
      └─> fetch_release_data
            └─> fetch_gitlab_issues
                  └─> fetch_merge_requests
                        └─> analyze_changes          (Repository Analyst agent + RAG)
                              └─> generate_release_notes   (Release Writer agent)
                                    └─> review_output       (QA agent)
                                          ├─ revise ──> generate_release_notes
                                          └─ continue ─> publish_to_slack  (Slack Publisher agent)
                                                            └─> persist_release ─> END
"""

from typing import Any

from app.workflows.nodes import ReleaseWorkflowNodes
from app.workflows.state import ReleaseWorkflowState


def build_release_workflow(nodes: ReleaseWorkflowNodes) -> Any:
    from langgraph.graph import END, START, StateGraph

    graph: Any = StateGraph(ReleaseWorkflowState)

    graph.add_node("fetch_release_data", nodes.fetch_release_data)
    graph.add_node("fetch_gitlab_issues", nodes.fetch_gitlab_issues)
    graph.add_node("fetch_merge_requests", nodes.fetch_merge_requests)
    graph.add_node("analyze_changes", nodes.analyze_changes)
    graph.add_node("generate_release_notes", nodes.generate_release_notes)
    graph.add_node("review_output", nodes.review_output)
    graph.add_node("publish_to_slack", nodes.publish_to_slack)
    graph.add_node("persist_release", nodes.persist_release)

    graph.add_edge(START, "fetch_release_data")
    graph.add_edge("fetch_release_data", "fetch_gitlab_issues")
    graph.add_edge("fetch_gitlab_issues", "fetch_merge_requests")
    graph.add_edge("fetch_merge_requests", "analyze_changes")
    graph.add_edge("analyze_changes", "generate_release_notes")
    graph.add_edge("generate_release_notes", "review_output")
    graph.add_conditional_edges(
        "review_output",
        nodes.decide_after_review,
        {"revise": "generate_release_notes", "continue": "publish_to_slack"},
    )
    graph.add_edge("publish_to_slack", "persist_release")
    graph.add_edge("persist_release", END)

    return graph.compile()
