import os
import yaml


def test_config_yaml_exists():
    """配置文件必须存在"""
    assert os.path.exists("config.yaml"), "config.yaml 不存在"


def test_config_yaml_valid():
    """配置文件必须是合法 YAML 且包含必要字段"""
    with open("config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    assert isinstance(config, dict)
    assert "domain" in config
    assert "apis" in config
    assert isinstance(config["apis"], list)
    assert "server" in config
    assert "port" in config["server"]


def test_config_apis_have_required_fields():
    """每个后端配置必须包含必要字段"""
    with open("config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    required = {"name", "custom_model_id", "target_model_id", "active"}
    for api in config.get("apis", []):
        missing = required - set(api.keys())
        assert not missing, f"后端 '{api.get('name', '?')}' 缺少字段: {missing}"
