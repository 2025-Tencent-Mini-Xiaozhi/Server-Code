package xiaozhi.modules.sys.event;

import org.springframework.context.ApplicationEvent;

/**
 * 参数更新事件
 */
public class ParamsUpdateEvent extends ApplicationEvent {

    private final String paramCode;
    private final String paramValue;

    public ParamsUpdateEvent(Object source, String paramCode, String paramValue) {
        super(source);
        this.paramCode = paramCode;
        this.paramValue = paramValue;
    }

    public String getParamCode() {
        return paramCode;
    }

    public String getParamValue() {
        return paramValue;
    }
}
