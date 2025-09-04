package xiaozhi.modules.sys.entity;

import java.util.Date;

import com.baomidou.mybatisplus.annotation.FieldFill;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableName;

import lombok.Data;
import lombok.EqualsAndHashCode;
import xiaozhi.common.entity.BaseEntity;

/**
 * 系统用户
 */
@Data
@EqualsAndHashCode(callSuper = false)
@TableName("sys_user")
public class SysUserEntity extends BaseEntity {
    /**
     * 用户名
     */
    private String username;
    /**
     * 密码
     */
    private String password;
    /**
     * 超级管理员 0：否 1：是
     */
    private Integer superAdmin;
    /**
     * 状态 0：停用 1：正常
     */
    private Integer status;
    /**
     * 用户姓名
     */
    private String realName;
    /**
     * 腾讯云secret_id
     */
    private String secretId;
    /**
     * 腾讯云secret_key
     */
    private String secretKey;
    /**
     * 更新者
     */
    @TableField(fill = FieldFill.INSERT_UPDATE)
    private Long updater;
    /**
     * 更新时间
     */
    @TableField(fill = FieldFill.INSERT_UPDATE)
    private Date updateDate;

    /**
     * 人脸编码数据
     */
    private String faceEncoding;

    /**
     * 人脸图片路径
     */
    private String faceImagePath;

    /**
     * 人脸注册时间
     */
    private Date faceRegisteredAt;

    /**
     * 是否启用人脸识别 0：否 1：是
     */
    private Integer faceEnabled;

}