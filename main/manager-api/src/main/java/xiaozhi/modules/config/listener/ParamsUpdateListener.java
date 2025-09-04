package xiaozhi.modules.config.listener;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.event.EventListener;
import org.springframework.stereotype.Component;

import lombok.extern.slf4j.Slf4j;
import xiaozhi.modules.config.service.EnvConfigService;
import xiaozhi.modules.sys.event.ParamsUpdateEvent;

/**
 * 参数更新事件监听器
 */
@Slf4j
@Component
public class ParamsUpdateListener {

    @Autowired
    private EnvConfigService envConfigService;

    @EventListener
    public void handleParamsUpdate(ParamsUpdateEvent event) {
        String paramCode = event.getParamCode();

        // 如果是智能体相关参数，更新.env文件
        if (isAgentParameter(paramCode)) {
            try {
                log.info("Detected agent parameter update: {}, updating MCP .env file", paramCode);
                envConfigService.updateMcpEnvConfig();
            } catch (Exception e) {
                log.error("Failed to update MCP env config after parameter update: {}", paramCode, e);
            }
        }
    }

    /**
     * 判断是否为智能体相关参数
     */
    private boolean isAgentParameter(String paramCode) {
        return "agent_model".equals(paramCode) || "agent_api_key".equals(paramCode);
    }
}
