import logging
logging.getLogger().setLevel(logging.INFO)
import os, sys
import pathlib
import yaml
import shutil
import subprocess
import functools
import types
import re
from collections import defaultdict
import inspect
import copy

import jsonpath_ng

from . import env
from . import run

VARIABLE_OVERRIDES_FILENAME = "000__ci_metadata/variable_overrides.yaml"

project = None # the project config will be populated in init()

class TempValue(object):
    """This context changes temporarily the value of a configuration field"""

    def __init__(self, config, key, value):
        self.config = config
        self.key = key
        self.value = value
        self.prev_value = None

    def __enter__(self):
        self.prev_value = self.config.get_config(self.key, print=False)
        self.config.set_config(self.key, self.value)

        return True

    def __exit__(self, ex_type, ex_value, exc_traceback):
        self.config.set_config(self.key, self.prev_value)

        return False # If we returned True here, any exception would be suppressed!


class Config:
    def __init__(self, config_path):
        self.config_path = config_path

        if not self.config_path.exists():
            msg = f"Configuration file '{self.config_path}' does not exist :/"
            logging.error(msg)
            raise ValueError(msg)

        logging.info(f"Loading configuration from {self.config_path} ...")
        with open(self.config_path) as config_f:
            self.config = yaml.safe_load(config_f)

        if self.config is None:
            self.config = {}

        if not isinstance(self.config, dict):
            raise ValueError(f"YAML loaded from {self.config_path} isn't a dictionnary ({self.config.__class__.__name__})")


    def ensure_core_fields(self):
        """
        The JumpCI currently passes these values:
-----
cluster.name: mac
exec_list._only_: true
exec_list.test_ci: true
project.args:
- init
project.name: skeleton
-----
We will get rid of that when we remove the JumpCI.
        """

        # Define mandatory fields structure
        mandatory_fields = {
            "presets": {},  # Special case: always create as empty dict
            "cluster": dict.fromkeys(["name"]),
            "project": dict.fromkeys(["name", "args"]),
            "exec_list": dict.fromkeys(["_only_", "prepare", "pre_cleanup", "test"]),
            "ci_job": dict.fromkeys(["name", "project", "args"])
        }

        # Apply the mandatory field structure
        for section_name, section_fields in mandatory_fields.items():
            # Create section if it doesn't exist
            if section_name not in self.config:
                self.config[section_name] = {}

            # Handle special case for presets (always overwrite with empty dict)
            if section_name == "presets":
                self.config[section_name] = section_fields
                continue

            # Add missing fields to the section
            for field_name, default_value in section_fields.items():
                if field_name in self.config[section_name]:
                    continue
                self.config[section_name][field_name] = default_value

    def save_config_overrides(self):
        variable_overrides_path = env.ARTIFACT_DIR / VARIABLE_OVERRIDES_FILENAME

        if not variable_overrides_path.exists():
            logging.debug(f"save_config_overrides: {variable_overrides_path} does not exist, nothing to save.")
            self.config["overrides"] = {}
            return

        with open(variable_overrides_path) as f:
            variable_overrides = yaml.safe_load(f)

        self.config["overrides"] = variable_overrides

    def apply_config_overrides(self, *, ignore_not_found=False, variable_overrides_path=None, log=True):
        if variable_overrides_path is None:
            variable_overrides_path = env.ARTIFACT_DIR / VARIABLE_OVERRIDES_FILENAME

        if not variable_overrides_path.exists():
            logging.debug(f"apply_config_overrides: {variable_overrides_path} does not exist, nothing to override.")

            return

        with open(variable_overrides_path) as f:
            variable_overrides = yaml.safe_load(f)

        if not isinstance(variable_overrides, dict):
            msg = f"Wrong type for the variable overrides file. Expected a dictionnary, got {variable_overrides.__class__.__name__}"
            logging.fatal(msg)
            raise ValueError(msg)

        for key, value in variable_overrides.items():
            MAGIC_DEFAULT_VALUE = object()
            handled_secretly = True # current_value MUST NOT be printed below.
            current_value = self.get_config(key, MAGIC_DEFAULT_VALUE, print=False, warn=False, handled_secretly=handled_secretly)
            if current_value == MAGIC_DEFAULT_VALUE:
                if ignore_not_found:
                    continue

                raise ValueError(f"Config key '{key}' does not exist, and cannot create it at the moment :/")

            self.set_config(key, value, print=False)
            actual_value = self.get_config(key, print=False) # ensure that key has been set, raises an exception otherwise
            if log:
                logging.info(f"config override: {key} --> {actual_value}")


    def apply_preset(self, name):
        values = self.get_preset(name)
        if not values:
            raise ValueError(f"No preset found with name '{name}'")

        logging.info(f"Applying preset '{name}' ==> {values}")
        for key, value in values.items():
            if key == "extends":
                for extend_name in value:
                    self.apply_preset(extend_name)
                continue

            msg = f"preset[{name}] {key} --> {value}"
            logging.info(msg)
            with open(env.ARTIFACT_DIR / "presets_applied", "a") as f:
                print(msg, file=f)

            self.set_config(key, value, print=False)

    def load_presets(self, preset_dir):
        for preset_file in preset_dir.glob("*.yaml"):
            with open(preset_file) as preset_f:
                preset_dict = yaml.safe_load(preset_f)
            if "__multiple" in preset_dict:
                self.config["presets"].update(preset_dict)
            else:
                self.config["presets"][preset_file.stem] = preset_dict

        self.save_config()

    def get_preset(self, name):
        return self.config["presets"].get(name)

    def apply_presets_from_project_args(self):

        for arg_name in self.get_config("project.args", print=False) or []:
            self.apply_preset(arg_name)


    def has_config(self, jsonpath):
        try:
            _ = jsonpath_ng.parse(jsonpath).find(self.config)[0].value # raises an IndexError if jsonpath isn't found
            return True
        except IndexError as ex:
            return False

    def get_config(self, jsonpath, default_value=..., warn=True, print=True, handled_secretly=False):
        try:
            value = jsonpath_ng.parse(jsonpath).find(self.config)[0].value
        except IndexError as ex:
            if default_value != ...:
                if warn:
                    logging.warning(f"get_config: {jsonpath} --> missing. Returning the default value: {default_value}")
                return default_value

            logging.error(f"get_config: {jsonpath} --> {ex}")
            raise KeyError(f"Key '{jsonpath}' not found in {self.config_path}")

        if isinstance(value, str) and value.startswith("*$@"):
            print = False

        value = self.resolve_reference(value, handled_secretly)

        if print and not handled_secretly:
            logging.info(f"get_config: {jsonpath} --> {value}")

        return value


    def set_config(self, jsonpath, value, print=True):
        try:
            self.get_config(jsonpath, print=False, handled_secretly=True) # will raise an exception if the jsonpath does not exist
            jsonpath_ng.parse(jsonpath).update(self.config, value)
        except Exception as ex:
            logging.error(f"set_config: {jsonpath}={value} --> {ex}")
            raise

        if print:
            logging.info(f"set_config: {jsonpath} --> {value}")

        self.save_config()


    def save_config(self):
        with open(self.config_path, "w") as f:
            yaml.dump(self.config, f, indent=4, default_flow_style=False, sort_keys=False)


    def resolve_reference(self, value, handled_secretly=False):
        if not isinstance(value, str): return value
        if "@" not in value: return value

        # --- #

        def secret_file_dereference():
            if not handled_secretly:
                msg = f"{value} is a secret dereference, but get_config(..., handled_secretly=False). Aborting"
                logging.fatal(msg)
                raise ValueError(msg)

            ref_key = value.removeprefix("*$@")
            ref_value = self.get_config(ref_key, print=False)

            secret_dir = pathlib.Path(os.environ[self.get_config("secrets.dir.env_key", print=False)])
            secret_value = (secret_dir / ref_value).read_text().strip()

            return secret_value


        # --- #

        def simple_dereference():
            ref_key = value[1:]
            return self.get_config(ref_key)


        def multi_dereference():
            new_value = value
            for ref in re.findall(r"\{@.*?\}", value):
                ref_key = ref.strip("{@}")
                ref_value = self.get_config(ref_key, print=False)
                new_value = new_value.replace(ref, str(ref_value))

            return new_value

        # --- #

        if value.startswith("*$@"):
            return secret_file_dereference()

        if value.startswith("*@"):
            # value can be printed here, it's a reference to a secret, not a secret value
            msg = f"resolve_reference: '*@' references not supported (not sure how to handle it wrt to secrets) --> {value}"
            logging.fatal(msg)
            raise ValueError(msg)

        if not (value.startswith("@") or "{@" in value):
            # don't go further if the derefence anchor isn't found
            return value

        # --- #


        new_value = simple_dereference() if value.startswith("@") \
            else multi_dereference()

        if not handled_secretly:
            logging.info(f"resolve_reference: {value} ==> '{new_value}'")

        return copy.deepcopy(new_value)


    def filter_out_used_overrides(self):
        """
        Remove the config fields that apply to the current config.
        Keep only the overrides that do not apply.
        """

        overrides = self.get_config("overrides", {}) or {}
        new_overrides = {}
        for key, value in overrides.items():
            if self.has_config(key):
                continue
            new_overrides[key] = value

        self.set_config("overrides", new_overrides, print=False)


def __get_config_path(orchestration_dir):
    config_file_src = orchestration_dir / "config.yaml"
    config_path_final = pathlib.Path(env.ARTIFACT_DIR / "config.yaml")

    if not config_file_src.exists():
        raise ValueError(f"Cannot find the source config file at {config_file_src}")

    if config_path_final.exists():
        logging.info(f"Reloading the config file from FORGE project directory {config_file_src} ...")
        return config_path_final, config_file_src

    logging.info(f"Copying the configuration from {config_file_src} to the artifact dir ...")
    shutil.copyfile(config_file_src, config_path_final)

    return config_path_final, config_file_src


REQUIRES_ANNOTATION_ARG_NAME = "_cfg"

# annotation
def requires(**config_kwargs):
    def decorator(func):

        if REQUIRES_ANNOTATION_ARG_NAME not in inspect.signature(func).parameters.keys():
            raise SyntaxError(f"Function '{func.__name__}' must accept "
                              f"a {REQUIRES_ANNOTATION_ARG_NAME} parameter.")

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            nonlocal config_kwargs

            config_obj = types.SimpleNamespace()

            for field_name, config_path in config_kwargs.items():
                config_obj.__dict__[field_name] = project.get_config(config_path)

            kwargs[REQUIRES_ANNOTATION_ARG_NAME] = config_obj

            return func(*args, **kwargs)
        return wrapper
    return decorator


def init(orchestration_dir, *, apply_config_overrides=True):
    global project

    if project:
        logging.info("config.init: project config already configured.")
        return

    config_path, src_config = __get_config_path(orchestration_dir)

    project = Config(config_path)

    repo_var_overrides = env.ARTIFACT_DIR / VARIABLE_OVERRIDES_FILENAME

    if not apply_config_overrides:
        logging.info("config.init: running with 'apply_config_overrides', "
                     "skipping the overrides. Saving it as 'overrides' "
                     "field in the project configuration.")
        project.save_config_overrides()
        project.save_config()
        return


    project.ensure_core_fields()
    project.load_presets(src_config.parent / "presets.d")
    project.apply_config_overrides()
    project.apply_presets_from_project_args()
    project.apply_config_overrides() # reapply so that the value overrides are applied last
