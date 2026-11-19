import pytest


@pytest.fixture(autouse=True)
def requirement_properties(request):
    marker = request.node.get_closest_marker("requirement")
    if marker:
        request.node.user_properties.append(("requirements", ",".join(marker.args)))
