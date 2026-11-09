from dify_plugin import DifyPluginEnv, Plugin

# Large Office files and OCR jobs can take several minutes.
plugin = Plugin(DifyPluginEnv(MAX_REQUEST_TIMEOUT=960))

if __name__ == "__main__":
    plugin.run()
