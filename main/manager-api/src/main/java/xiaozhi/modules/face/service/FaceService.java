package xiaozhi.modules.face.service;

import xiaozhi.modules.face.dto.FaceRegisterDTO;
import xiaozhi.modules.face.dto.FaceRegisterResultDTO;
import xiaozhi.modules.face.dto.FaceCheckResultDTO;

/**
 * 人脸识别服务接口
 */
public interface FaceService {

    /**
     * 检查人脸是否已存在（用于注册前验证）
     * 
     * @param imageName 图片文件名
     * @return 检查结果
     */
    FaceCheckResultDTO checkFace(String imageName);

    /**
     * 注册用户人脸
     * 
     * @param faceRegisterDTO 人脸注册参数
     * @return 注册结果
     */
    FaceRegisterResultDTO registerFace(FaceRegisterDTO faceRegisterDTO);

    /**
     * 检查xiaozhi-server服务是否可用
     * 
     * @return 是否可用
     */
    boolean isXiaozhiServerAvailable();
}
