from config.settings import QA_THRESHOLD, MAX_RETRIES, FLUX_ENDPOINT


def test_config_values():
    assert QA_THRESHOLD == 7.0
    assert MAX_RETRIES == 2


def test_flux_endpoint():
    assert FLUX_ENDPOINT.startswith("https://")
    assert "modal.run" in FLUX_ENDPOINT


def test_imports():
    from my_agents.image_agent import image_agent
    assert image_agent.name == "Image Generation Agent"

    from my_agents.qa_agent import qa_agent
    assert qa_agent.name == "QA Agent"