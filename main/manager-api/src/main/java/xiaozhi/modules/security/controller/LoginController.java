package xiaozhi.modules.security.controller;

import java.io.IOException;
import java.util.Calendar;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.servlet.http.HttpServletResponse;
import lombok.AllArgsConstructor;
import xiaozhi.common.constant.Constant;
import xiaozhi.common.exception.ErrorCode;
import xiaozhi.common.exception.RenException;
import xiaozhi.common.page.TokenDTO;
import xiaozhi.common.user.UserDetail;
import xiaozhi.common.utils.Result;
import xiaozhi.common.validator.AssertUtils;
import xiaozhi.common.validator.ValidatorUtils;
import xiaozhi.modules.security.dto.LoginDTO;
import xiaozhi.modules.security.dto.SmsVerificationDTO;
import xiaozhi.modules.security.password.PasswordUtils;
import xiaozhi.modules.security.service.CaptchaService;
import xiaozhi.modules.security.service.SysUserTokenService;
import xiaozhi.modules.security.user.SecurityUser;
import xiaozhi.modules.sys.dto.PasswordDTO;
import xiaozhi.modules.sys.dto.RetrievePasswordDTO;
import xiaozhi.modules.sys.dto.SysUserDTO;
import xiaozhi.modules.sys.service.SysDictDataService;
import xiaozhi.modules.sys.service.SysParamsService;
import xiaozhi.modules.sys.service.SysUserService;
import xiaozhi.modules.sys.vo.SysDictDataItem;
import xiaozhi.modules.face.service.FaceService;
import xiaozhi.modules.face.dto.FaceRegisterDTO;
import xiaozhi.modules.face.dto.FaceRegisterResultDTO;
import xiaozhi.modules.face.dto.FaceCheckResultDTO;

/**
 * 登录控制层
 */
@AllArgsConstructor
@RestController
@RequestMapping("/user")
@Tag(name = "登录管理")
public class LoginController {
    private final SysUserService sysUserService;
    private final SysUserTokenService sysUserTokenService;
    private final CaptchaService captchaService;
    private final SysParamsService sysParamsService;
    private final SysDictDataService sysDictDataService;
    private final FaceService faceService;

    @GetMapping("/captcha")
    @Operation(summary = "验证码")
    public void captcha(HttpServletResponse response, String uuid) throws IOException {
        // uuid不能为空
        AssertUtils.isBlank(uuid, ErrorCode.IDENTIFIER_NOT_NULL);
        // 生成验证码
        captchaService.create(response, uuid);
    }

    @PostMapping("/smsVerification")
    @Operation(summary = "短信验证码")
    public Result<Void> smsVerification(@RequestBody SmsVerificationDTO dto) {
        // 验证图形验证码
        boolean validate = captchaService.validate(dto.getCaptchaId(), dto.getCaptcha(), true);
        if (!validate) {
            throw new RenException("图形验证码错误");
        }
        Boolean isMobileRegister = sysParamsService
                .getValueObject(Constant.SysMSMParam.SERVER_ENABLE_MOBILE_REGISTER.getValue(), Boolean.class);
        if (!isMobileRegister) {
            throw new RenException("没有开启手机注册，没法使用短信验证码功能");
        }
        // 发送短信验证码
        captchaService.sendSMSValidateCode(dto.getPhone());
        return new Result<>();
    }

    @PostMapping("/login")
    @Operation(summary = "登录")
    public Result<TokenDTO> login(@RequestBody LoginDTO login) {
        // 验证是否正确输入验证码
        boolean validate = captchaService.validate(login.getCaptchaId(), login.getCaptcha(), true);
        if (!validate) {
            throw new RenException("图形验证码错误，请重新获取");
        }
        // 按照用户名获取用户
        SysUserDTO userDTO = sysUserService.getByUsername(login.getUsername());
        // 判断用户是否存在
        if (userDTO == null) {
            throw new RenException("请检测用户和密码是否输入错误");
        }
        // 判断密码是否正确，不一样则进入if
        if (!PasswordUtils.matches(login.getPassword(), userDTO.getPassword())) {
            throw new RenException("请检测用户和密码是否输入错误");
        }
        return sysUserTokenService.createToken(userDTO.getId());
    }

    @PostMapping("/register")
    @Operation(summary = "注册")
    public Result<Void> register(@RequestBody LoginDTO login) {
        if (!sysUserService.getAllowUserRegister()) {
            throw new RenException("当前不允许普通用户注册");
        }
        // 是否开启手机注册
        Boolean isMobileRegister = sysParamsService
                .getValueObject(Constant.SysMSMParam.SERVER_ENABLE_MOBILE_REGISTER.getValue(), Boolean.class);
        boolean validate;
        if (isMobileRegister) {
            // 验证用户是否是手机号码
            boolean validPhone = ValidatorUtils.isValidPhone(login.getUsername());
            if (!validPhone) {
                throw new RenException("用户名不是手机号码，请重新输入");
            }
            // 验证短信验证码是否正常
            validate = captchaService.validateSMSValidateCode(login.getUsername(), login.getMobileCaptcha(), false);
            if (!validate) {
                throw new RenException("手机验证码错误，请重新获取");
            }
        } else {
            // 验证是否正确输入验证码
            validate = captchaService.validate(login.getCaptchaId(), login.getCaptcha(), true);
            if (!validate) {
                throw new RenException("图形验证码错误，请重新获取");
            }
        }

        // 按照用户名获取用户
        SysUserDTO userDTO = sysUserService.getByUsername(login.getUsername());
        if (userDTO != null) {
            throw new RenException("此手机号码已经注册过");
        }

        // 如果提供了人脸图片，先检查人脸是否已存在
        if (login.getFaceImageName() != null && !login.getFaceImageName().trim().isEmpty()) {
            try {
                FaceCheckResultDTO faceCheckResult = faceService.checkFace(login.getFaceImageName());

                if (!faceCheckResult.getSuccess()) {
                    throw new RenException("人脸检查失败: " + faceCheckResult.getMessage());
                }

                if (!faceCheckResult.getFaceDetected()) {
                    throw new RenException("图片中未检测到人脸，请选择包含清晰人脸的图片");
                }

                if (faceCheckResult.getExists()) {
                    String existingUserName = faceCheckResult.getExistingUser() != null
                            ? faceCheckResult.getExistingUser().getRealName()
                            : "其他用户";
                    throw new RenException("该人脸已被用户 '" + existingUserName + "' 注册过，请使用其他图片");
                }

            } catch (Exception e) {
                // 如果是我们抛出的RenException，直接传递
                if (e instanceof RenException) {
                    throw e;
                }
                // 其他异常转换为注册失败
                throw new RenException("人脸验证服务异常，请稍后重试: " + e.getMessage());
            }
        }

        userDTO = new SysUserDTO();
        userDTO.setUsername(login.getUsername());
        userDTO.setPassword(login.getPassword());
        userDTO.setRealName(login.getRealName());
        userDTO.setSecretId(login.getSecretId());
        userDTO.setSecretKey(login.getSecretKey());
        sysUserService.save(userDTO);

        // 如果提供了人脸图片，进行人脸注册（前面已经验证过不重复）
        System.out.println("检查人脸图片参数: " + login.getFaceImageName());
        if (login.getFaceImageName() != null && !login.getFaceImageName().trim().isEmpty()) {
            try {
                System.out.println("开始进行人脸注册，用户ID: " + userDTO.getId() + ", 图片名: " + login.getFaceImageName());

                FaceRegisterDTO faceRegisterDTO = new FaceRegisterDTO();
                faceRegisterDTO.setUserId(userDTO.getId());
                faceRegisterDTO.setRealName(login.getRealName());
                faceRegisterDTO.setImageName(login.getFaceImageName());

                FaceRegisterResultDTO faceResult = faceService.registerFace(faceRegisterDTO);

                System.out.println("人脸注册结果: " + (faceResult != null ? faceResult.getSuccess() : "null"));
                if (faceResult != null && !faceResult.getSuccess()) {
                    // 人脸注册失败，但用户已创建，只记录警告
                    // 这里可以选择是否要删除已创建的用户，根据业务需求决定
                    // 目前选择保留用户，只是人脸注册失败
                    System.out.println("用户注册成功，但人脸注册失败: " + faceResult.getMessage());
                } else if (faceResult != null) {
                    System.out.println("人脸注册成功!");
                }
            } catch (Exception e) {
                // 人脸注册异常，记录日志但不影响用户注册
                System.out.println("人脸注册过程中出现异常: " + e.getMessage());
                e.printStackTrace();
            }
        } else {
            System.out.println("没有提供人脸图片，跳过人脸注册");
        }

        return new Result<>();
    }

    @GetMapping("/info")
    @Operation(summary = "用户信息获取")
    public Result<UserDetail> info() {
        UserDetail user = SecurityUser.getUser();
        Result<UserDetail> result = new Result<>();
        result.setData(user);
        return result;
    }

    @PutMapping("/change-password")
    @Operation(summary = "修改用户密码")
    public Result<?> changePassword(@RequestBody PasswordDTO passwordDTO) {
        // 判断非空
        ValidatorUtils.validateEntity(passwordDTO);
        Long userId = SecurityUser.getUserId();
        sysUserTokenService.changePassword(userId, passwordDTO);
        return new Result<>();
    }

    @PutMapping("/retrieve-password")
    @Operation(summary = "找回密码")
    public Result<?> retrievePassword(@RequestBody RetrievePasswordDTO dto) {
        // 是否开启手机注册
        Boolean isMobileRegister = sysParamsService
                .getValueObject(Constant.SysMSMParam.SERVER_ENABLE_MOBILE_REGISTER.getValue(), Boolean.class);
        if (!isMobileRegister) {
            throw new RenException("没有开启手机注册，没法使用找回密码功能");
        }
        // 判断非空
        ValidatorUtils.validateEntity(dto);
        // 验证用户是否是手机号码
        boolean validPhone = ValidatorUtils.isValidPhone(dto.getPhone());
        if (!validPhone) {
            throw new RenException("输入的手机号码格式不正确");
        }

        // 按照用户名获取用户
        SysUserDTO userDTO = sysUserService.getByUsername(dto.getPhone());
        if (userDTO == null) {
            throw new RenException("输入的手机号码未注册");
        }
        // 验证短信验证码是否正常
        boolean validate = captchaService.validateSMSValidateCode(dto.getPhone(), dto.getCode(), false);
        // 判断是否通过验证
        if (!validate) {
            throw new RenException("输入的手机验证码错误");
        }

        sysUserService.changePasswordDirectly(userDTO.getId(), dto.getPassword());
        return new Result<>();
    }

    @GetMapping("/pub-config")
    @Operation(summary = "公共配置")
    public Result<Map<String, Object>> pubConfig() {
        Map<String, Object> config = new HashMap<>();
        config.put("enableMobileRegister", sysParamsService
                .getValueObject(Constant.SysMSMParam.SERVER_ENABLE_MOBILE_REGISTER.getValue(), Boolean.class));
        config.put("version", Constant.VERSION);
        config.put("year", "©" + Calendar.getInstance().get(Calendar.YEAR));
        config.put("allowUserRegister", sysUserService.getAllowUserRegister());
        List<SysDictDataItem> list = sysDictDataService.getDictDataByType(Constant.DictType.MOBILE_AREA.getValue());
        config.put("mobileAreaList", list);
        config.put("beianIcpNum", sysParamsService.getValue(Constant.SysBaseParam.BEIAN_ICP_NUM.getValue(), true));
        config.put("beianGaNum", sysParamsService.getValue(Constant.SysBaseParam.BEIAN_GA_NUM.getValue(), true));
        config.put("name", sysParamsService.getValue(Constant.SysBaseParam.SERVER_NAME.getValue(), true));

        return new Result<Map<String, Object>>().ok(config);
    }
}