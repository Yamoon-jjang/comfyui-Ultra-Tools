class UltraWorkflowTimer:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "Time": (
                    "STRING",
                    {
                        "default": "Idle",
                        "multiline": False,
                    },
                ),
                "History": (
                    "STRING",
                    {
                        "default": " ",
                        "multiline": True,
                    },
                ),
            }
        }

    RETURN_TYPES = ()
    RETURN_NAMES = ()
    FUNCTION = "run"
    OUTPUT_NODE = True
    CATEGORY = "Ultra Tools"

    def run(self, Time="Idle", History=" "):
        return ()


NODE_CLASS_MAPPINGS = {
    "UltraWorkflowTimer": UltraWorkflowTimer,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "UltraWorkflowTimer": "Ultra Tools Workflow Timer",
}