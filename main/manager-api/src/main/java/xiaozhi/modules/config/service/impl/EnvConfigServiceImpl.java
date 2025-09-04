package xiaozhi.modules.config.service.impl;

import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.FileReader;
import java.io.FileWriter;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.List;

import org.apache.commons.lang3.StringUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.annotation.Lazy;
import org.springframework.stereotype.Service;

import lombok.extern.slf4j.Slf4j;
import xiaozhi.modules.config.service.EnvConfigService;
import xiaozhi.modules.sys.service.SysParamsService;

/**
 * .env文件配置服务实现
 */
@Slf4j
@Service
public class EnvConfigServiceImpl implements EnvConfigService {

    @Autowired
    @Lazy
    private SysParamsService sysParamsService;

    // MCP .env文件路径
    private static final String MCP_ENV_FILE_PATH = "/root/xiaozhi-esp32-server/main/xiaozhi-server/core/providers/tools/server_mcp/.env";

    @Override
    public void updateMcpEnvConfig() {
        try {
            // 获取参数值
            String agentModel = sysParamsService.getValue("agent_model", true);
            String agentApiKey = sysParamsService.getValue("agent_api_key", true);

            // 如果参数为空或默认值，则不更新
            if (StringUtils.isBlank(agentModel) || "your_agent_model".equals(agentModel) ||
                    StringUtils.isBlank(agentApiKey) || "your_agent_api_key".equals(agentApiKey)) {
                log.warn("Agent model or API key is not configured, skipping .env update");
                return;
            }

            // 确保目录存在
            Path envFilePath = Paths.get(MCP_ENV_FILE_PATH);
            Path parentDir = envFilePath.getParent();
            if (!Files.exists(parentDir)) {
                Files.createDirectories(parentDir);
                log.info("Created directory: {}", parentDir);
            }

            // 读取现有文件内容
            List<String> lines = new ArrayList<>();
            if (Files.exists(envFilePath)) {
                try (BufferedReader reader = new BufferedReader(new FileReader(MCP_ENV_FILE_PATH))) {
                    String line;
                    while ((line = reader.readLine()) != null) {
                        lines.add(line);
                    }
                }
            } else {
                // 如果文件不存在，添加注释
                lines.add("# 通义千问模型配置");
            }

            // 更新或添加配置
            boolean agentModelUpdated = false;
            boolean agentApiKeyUpdated = false;

            for (int i = 0; i < lines.size(); i++) {
                String line = lines.get(i);
                if (line.startsWith("AGENT_MODEL=")) {
                    lines.set(i, "AGENT_MODEL=" + agentModel);
                    agentModelUpdated = true;
                } else if (line.startsWith("AGENT_API_KEY=")) {
                    lines.set(i, "AGENT_API_KEY=" + agentApiKey);
                    agentApiKeyUpdated = true;
                }
            }

            // 如果没有找到配置项，则添加
            if (!agentModelUpdated) {
                lines.add("AGENT_MODEL=" + agentModel);
            }
            if (!agentApiKeyUpdated) {
                lines.add("AGENT_API_KEY=" + agentApiKey);
            }

            // 写入文件
            try (BufferedWriter writer = new BufferedWriter(new FileWriter(MCP_ENV_FILE_PATH))) {
                for (String line : lines) {
                    writer.write(line);
                    writer.newLine();
                }
            }

            log.info("Successfully updated MCP .env configuration file at: {}", MCP_ENV_FILE_PATH);
            log.debug("Agent Model: {}, Agent API Key: {}***", agentModel,
                    agentApiKey.length() > 4 ? agentApiKey.substring(0, 4) : "****");

        } catch (IOException e) {
            log.error("Failed to update MCP .env configuration file", e);
        } catch (Exception e) {
            log.error("Unexpected error while updating MCP .env configuration", e);
        }
    }
}
