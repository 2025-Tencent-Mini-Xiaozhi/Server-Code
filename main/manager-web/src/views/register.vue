<template>
  <div class="welcome" @keyup.enter="register">
    <el-container style="height: 100%;">
      <!-- 保持相同的头部 -->
      <el-header>
        <div style="display: flex;align-items: center;margin-top: 15px;margin-left: 10px;gap: 10px;">
          <img loading="lazy" alt="" src="@/assets/xiaozhi-logo.png" style="width: 45px;height: 45px;" />
          <img loading="lazy" alt="" src="@/assets/xiaozhi-ai.png" style="height: 18px;" />
        </div>
      </el-header>
      <div class="login-person">
        <img loading="lazy" alt="" src="@/assets/login/register-person.png" style="width: 100%;" />
      </div>
      <el-main style="position: relative;">
        <div class="login-box">
          <!-- 修改标题部分 -->
          <div style="display: flex;align-items: center;gap: 20px;margin-bottom: 39px;padding: 0 30px;">
            <img loading="lazy" alt="" src="@/assets/login/hi.png" style="width: 34px;height: 34px;" />
            <div class="login-text">注册</div>
            <div class="login-welcome">
              WELCOME TO REGISTER
            </div>
          </div>

          <div style="padding: 0 30px;">
            <form @submit.prevent="register">
              <!-- 用户名/手机号输入框 -->
              <div class="input-box" v-if="!enableMobileRegister">
                <img loading="lazy" alt="" class="input-icon" src="@/assets/login/username.png" />
                <el-input v-model="form.username" placeholder="请输入用户名" />
              </div>

              <!-- 手机号注册部分 -->
              <template v-if="enableMobileRegister">
                <div class="input-box">
                  <div style="display: flex; align-items: center; width: 100%;">
                    <el-select v-model="form.areaCode" style="width: 220px; margin-right: 10px;">
                      <el-option v-for="item in mobileAreaList" :key="item.key" :label="`${item.name} (${item.key})`"
                        :value="item.key" />
                    </el-select>
                    <el-input v-model="form.mobile" placeholder="请输入手机号码" />
                  </div>
                </div>

                <div style="display: flex; align-items: center; margin-top: 20px; width: 100%; gap: 10px;">
                  <div class="input-box" style="width: calc(100% - 130px); margin-top: 0;">
                    <img loading="lazy" alt="" class="input-icon" src="@/assets/login/shield.png" />
                    <el-input v-model="form.captcha" placeholder="请输入验证码" style="flex: 1;" />
                  </div>
                  <img loading="lazy" v-if="captchaUrl" :src="captchaUrl" alt="验证码"
                    style="width: 150px; height: 40px; cursor: pointer;" @click="fetchCaptcha" />
                </div>

                <!-- 手机验证码 -->

                <div style="display: flex; align-items: center; margin-top: 20px; width: 100%; gap: 10px;">
                  <div class="input-box" style="width: calc(100% - 130px); margin-top: 0;">
                    <img loading="lazy" alt="" class="input-icon" src="@/assets/login/phone.png" />
                    <el-input v-model="form.mobileCaptcha" placeholder="请输入手机验证码" style="flex: 1;" maxlength="6" />
                  </div>
                  <el-button type="primary" class="send-captcha-btn" :disabled="!canSendMobileCaptcha"
                    @click="sendMobileCaptcha">
                    <span>
                      {{ countdown > 0 ? `${countdown}秒后重试` : '发送验证码' }}
                    </span>
                  </el-button>
                </div>
              </template>

              <!-- 密码输入框 -->
              <div class="input-box">
                <img loading="lazy" alt="" class="input-icon" src="@/assets/login/password.png" />
                <el-input v-model="form.password" placeholder="请输入密码" type="password" show-password />
              </div>

              <!-- 新增确认密码 -->
              <div class="input-box">
                <img loading="lazy" alt="" class="input-icon" src="@/assets/login/password.png" />
                <el-input v-model="form.confirmPassword" placeholder="请确认密码" type="password" show-password />
              </div>

              <!-- 新增姓名字段 -->
              <div class="input-box">
                <img loading="lazy" alt="" class="input-icon" src="@/assets/login/username.png" />
                <el-input v-model="form.realName" placeholder="请输入姓名" />
              </div>

              <!-- 人脸图片选择区域 -->
              <div class="face-selection-section">
                <div class="section-title">
                  <i class="el-icon-picture-outline"></i>
                  选择人脸图片（可选）
                </div>
                <div class="face-search-box">
                  <el-input
                    v-model="faceSearchDeviceId"
                    placeholder="请输入设备码进行检索，如：2b_c8_58"
                    class="face-search-input"
                    @keyup.enter.native="loadFaceImages"
                    clearable>
                  </el-input>
                  <el-button type="primary" size="small" @click="loadFaceImages">搜索</el-button>
                </div>
                
                <!-- 图片横向滚动展示区域 -->
                <div class="face-images-container" v-if="faceImages.length > 0">
                  <div class="face-images-scroll" ref="faceImagesScroll">
                    <div 
                      v-for="(image, index) in faceImages" 
                      :key="image.name"
                      class="face-image-item"
                      :class="{ 'selected': selectedFaceImage === image.name }"
                      @click="selectFaceImage(image)"
                    >
                      <img 
                        :src="getFaceImageUrl(image.name)" 
                        :alt="image.name"
                        @error="handleFaceImageError"
                      />
                      <div class="image-overlay">
                        <i v-if="selectedFaceImage === image.name" class="el-icon-check"></i>
                      </div>
                      <div class="image-info">
                        <span>{{ formatImageTime(image.timestamp) }}</span>
                      </div>
                    </div>
                  </div>
                  
                  <!-- 进度条 -->
                  <div class="scroll-progress-container">
                    <div class="scroll-progress-bar">
                      <div 
                        class="scroll-progress-thumb" 
                        :style="{ left: scrollProgress + '%' }"
                        @mousedown="startDrag"
                      ></div>
                    </div>
                  </div>
                  
                  <!-- 选中的图片信息 -->
                  <div v-if="selectedFaceImage" class="selected-image-info">
                    <i class="el-icon-success text-success"></i>
                    已选择图片：{{ selectedFaceImage }}
                    <el-button type="text" size="mini" @click="clearFaceSelection">取消选择</el-button>
                  </div>
                </div>
                
                <!-- 空状态提示 -->
                <div v-else-if="faceImagesLoaded && faceImages.length === 0" class="face-empty-state">
                  <i class="el-icon-picture-outline"></i>
                  <p>未找到相关人脸图片</p>
                  <p class="empty-tip">请尝试输入其他设备码进行搜索</p>
                </div>
              </div>

              <!-- 新增腾讯云Secret ID字段 -->
              <div class="input-box">
                <img loading="lazy" alt="" class="input-icon" src="@/assets/login/shield.png" />
                <el-input v-model="form.secretId" placeholder="请输入腾讯云Secret ID" />
              </div>

              <!-- 新增腾讯云Secret Key字段 -->
              <div class="input-box">
                <img loading="lazy" alt="" class="input-icon" src="@/assets/login/shield.png" />
                <el-input v-model="form.secretKey" placeholder="请输入腾讯云Secret Key" type="password" show-password />
              </div>

              <!-- 验证码部分保持相同 -->
              <div v-if="!enableMobileRegister"
                style="display: flex; align-items: center; margin-top: 20px; width: 100%; gap: 10px;">
                <div class="input-box" style="width: calc(100% - 130px); margin-top: 0;">
                  <img loading="lazy" alt="" class="input-icon" src="@/assets/login/shield.png" />
                  <el-input v-model="form.captcha" placeholder="请输入验证码" style="flex: 1;" />
                </div>
                <img loading="lazy" v-if="captchaUrl" :src="captchaUrl" alt="验证码"
                  style="width: 150px; height: 40px; cursor: pointer;" @click="fetchCaptcha" />
              </div>

              <!-- 修改底部链接 -->
              <div style="font-weight: 400;font-size: 14px;text-align: left;color: #5778ff;margin-top: 20px;">
                <div style="cursor: pointer;" @click="goToLogin">已有账号？立即登录</div>
              </div>
            </form>
          </div>

          <!-- 修改按钮文本 -->
          <div class="login-btn" @click="register">立即注册</div>

          <!-- 保持相同的协议声明 -->
          <div style="font-size: 14px;color: #979db1;">
            注册即同意
            <div style="display: inline-block;color: #5778FF;cursor: pointer;">《用户协议》</div>
            和
            <div style="display: inline-block;color: #5778FF;cursor: pointer;">《隐私政策》</div>
          </div>
        </div>
      </el-main>

      <!-- 保持相同的页脚 -->
      <el-footer>
        <version-footer />
      </el-footer>
    </el-container>
  </div>
</template>

<script>
import Api from '@/apis/api';
import VersionFooter from '@/components/VersionFooter.vue';
import { getUUID, goToPage, showDanger, showSuccess, validateMobile } from '@/utils';
import { mapState } from 'vuex';

export default {
  name: 'register',
  components: {
    VersionFooter
  },
  computed: {
    ...mapState({
      allowUserRegister: state => state.pubConfig.allowUserRegister,
      enableMobileRegister: state => state.pubConfig.enableMobileRegister,
      mobileAreaList: state => state.pubConfig.mobileAreaList
    }),
    canSendMobileCaptcha() {
      return this.countdown === 0 && validateMobile(this.form.mobile, this.form.areaCode);
    }
  },
  data() {
    return {
      form: {
        username: '',
        password: '',
        confirmPassword: '',
        realName: '',
        secretId: '',
        secretKey: '',
        captcha: '',
        captchaId: '',
        areaCode: '+86',
        mobile: '',
        mobileCaptcha: ''
      },
      captchaUrl: '',
      countdown: 0,
      timer: null,
      // 人脸图片相关数据
      faceImages: [],
      faceSearchDeviceId: '',
      selectedFaceImage: '',
      faceImagesLoaded: false,
      faceImageUrls: {},
      scrollProgress: 0,
      isDragging: false
    }
  },
  mounted() {
    this.$store.dispatch('fetchPubConfig').then(() => {
      if (!this.allowUserRegister) {
        showDanger('当前不允许普通用户注册');
        setTimeout(() => {
          goToPage('/login');
        }, 1500);
      }
    });
    this.fetchCaptcha();
    
    // 设置滚动监听
    this.$nextTick(() => {
      const container = this.$refs.faceImagesScroll;
      if (container) {
        container.addEventListener('scroll', this.updateScrollProgress);
      }
    });
  },
  methods: {
    // 复用验证码获取方法
    fetchCaptcha() {
      this.form.captchaId = getUUID();
      Api.user.getCaptcha(this.form.captchaId, (res) => {
        if (res.status === 200) {
          const blob = new Blob([res.data], { type: res.data.type });
          this.captchaUrl = URL.createObjectURL(blob);

        } else {
          console.error('验证码加载异常:', error);
          showDanger('验证码加载失败，点击刷新');
        }
      });
    },

    // 封装输入验证逻辑
    validateInput(input, message) {
      if (!input.trim()) {
        showDanger(message);
        return false;
      }
      return true;
    },

    // 发送手机验证码
    sendMobileCaptcha() {
      if (!validateMobile(this.form.mobile, this.form.areaCode)) {
        showDanger('请输入正确的手机号码');
        return;
      }

      // 验证图形验证码
      if (!this.validateInput(this.form.captcha, '请输入图形验证码')) {
        this.fetchCaptcha();
        return;
      }

      // 清除可能存在的旧定时器
      if (this.timer) {
        clearInterval(this.timer);
        this.timer = null;
      }

      // 开始倒计时
      this.countdown = 60;
      this.timer = setInterval(() => {
        if (this.countdown > 0) {
          this.countdown--;
        } else {
          clearInterval(this.timer);
          this.timer = null;
        }
      }, 1000);

      // 调用发送验证码接口
      Api.user.sendSmsVerification({
        phone: this.form.areaCode + this.form.mobile,
        captcha: this.form.captcha,
        captchaId: this.form.captchaId
      }, (res) => {
        showSuccess('验证码发送成功');
      }, (err) => {
        showDanger(err.data.msg || '验证码发送失败');
        this.countdown = 0;
        this.fetchCaptcha();
      });
    },

    // 注册逻辑
    register() {
      if (this.enableMobileRegister) {
        // 手机号注册验证
        if (!validateMobile(this.form.mobile, this.form.areaCode)) {
          showDanger('请输入正确的手机号码');
          return;
        }
        if (!this.form.mobileCaptcha) {
          showDanger('请输入手机验证码');
          return;
        }
      } else {
        // 用户名注册验证
        if (!this.validateInput(this.form.username, '用户名不能为空')) {
          return;
        }
      }

      // 验证密码
      if (!this.validateInput(this.form.password, '密码不能为空')) {
        return;
      }
      if (this.form.password !== this.form.confirmPassword) {
        showDanger('两次输入的密码不一致')
        return
      }

      // 验证新增字段
      if (!this.validateInput(this.form.realName, '姓名不能为空')) {
        return;
      }
      if (!this.validateInput(this.form.secretId, '腾讯云Secret ID不能为空')) {
        return;
      }
      if (!this.validateInput(this.form.secretKey, '腾讯云Secret Key不能为空')) {
        return;
      }

      // 验证验证码
      if (!this.validateInput(this.form.captcha, '验证码不能为空')) {
        return;
      }

      if (this.enableMobileRegister) {
        this.form.username = this.form.areaCode + this.form.mobile
      }

      // 添加人脸图片信息到表单数据
      const submitForm = {
        ...this.form,
        faceImageName: this.selectedFaceImage || null
      };

      Api.user.register(submitForm, ({ data }) => {
        showSuccess('注册成功！')
        goToPage('/login')
      }, (err) => {
        showDanger(err.data.msg || '注册失败')
        if (err.data != null && err.data.msg != null && err.data.msg.indexOf('图形验证码') > -1) {
          this.fetchCaptcha()
        }
      })
    },

    goToLogin() {
      goToPage('/login')
    },

    // 人脸图片相关方法
    loadFaceImages() {
      if (!Api.face || !Api.face.getFaceImages) {
        console.warn('Face API not available');
        return;
      }

      Api.face.getFaceImages(
        (response) => {
          this.faceImagesLoaded = true;
          if (response.data.code === 0) {
            this.faceImages = response.data.data.map(item => ({
              name: item.name,
              size: item.size,
              timestamp: item.timestamp || Math.floor(Date.now() / 1000)
            }));
            // 预加载图片
            this.preloadFaceImages();
          } else {
            this.$message.error(response.data.msg || '获取人脸图片失败');
            this.faceImages = [];
          }
        },
        (error) => {
          this.faceImagesLoaded = true;
          console.error('加载人脸图片失败:', error);
          this.$message.error('加载人脸图片失败');
          this.faceImages = [];
        },
        this.faceSearchDeviceId // 传递设备码参数
      );
    },

    // 预加载人脸图片
    preloadFaceImages() {
      this.faceImages.forEach(image => {
        this.loadFaceImageAsBlob(image.name).then(blobUrl => {
          this.$set(this.faceImageUrls, image.name, blobUrl);
        }).catch(error => {
          console.warn(`Failed to load face image ${image.name}:`, error);
        });
      });
    },

    // 加载人脸图片为blob URL
    loadFaceImageAsBlob(imageName) {
      return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.open('GET', `/xiaozhi/face/images/${imageName}`, true);
        xhr.responseType = 'blob';
        
        // 添加认证头
        const token = localStorage.getItem('token');
        if (token) {
          const tokenObj = JSON.parse(token);
          xhr.setRequestHeader('Authorization', 'Bearer ' + tokenObj.token);
        }
        
        xhr.onload = function() {
          if (xhr.status === 200) {
            const blobUrl = URL.createObjectURL(xhr.response);
            resolve(blobUrl);
          } else {
            reject(new Error(`HTTP ${xhr.status}`));
          }
        };
        
        xhr.onerror = function() {
          reject(new Error('Network error'));
        };
        
        xhr.send();
      });
    },

    // 获取人脸图片URL
    getFaceImageUrl(imageName) {
      return this.faceImageUrls[imageName] || require('@/assets/home/equipment.png');
    },

    // 处理人脸图片加载错误
    handleFaceImageError(event) {
      event.target.src = require('@/assets/home/equipment.png');
    },

    // 选择人脸图片
    selectFaceImage(image) {
      this.selectedFaceImage = image.name;
    },

    // 清除人脸选择
    clearFaceSelection() {
      this.selectedFaceImage = '';
    },

    // 格式化图片时间
    formatImageTime(timestamp) {
      const date = new Date(timestamp * 1000);
      return date.toLocaleString('zh-CN', {
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
      });
    },

    // 更新滚动进度
    updateScrollProgress() {
      const container = this.$refs.faceImagesScroll;
      if (!container) return;

      const scrollLeft = container.scrollLeft;
      const maxScroll = container.scrollWidth - container.clientWidth;
      
      if (maxScroll > 0) {
        this.scrollProgress = (scrollLeft / maxScroll) * 100;
      } else {
        this.scrollProgress = 0;
      }
    },

    // 开始拖拽进度条
    startDrag(event) {
      this.isDragging = true;
      const container = this.$refs.faceImagesScroll;
      if (!container) return;

      const progressContainer = event.target.parentElement;
      const rect = progressContainer.getBoundingClientRect();
      
      const handleMouseMove = (e) => {
        if (!this.isDragging) return;
        
        const x = e.clientX - rect.left;
        const percentage = Math.max(0, Math.min(100, (x / rect.width) * 100));
        
        // 更新滚动位置
        const maxScroll = container.scrollWidth - container.clientWidth;
        const scrollLeft = (percentage / 100) * maxScroll;
        container.scrollLeft = scrollLeft;
        
        this.scrollProgress = percentage;
      };

      const handleMouseUp = () => {
        this.isDragging = false;
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
      };

      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      
      event.preventDefault();
    }
  },
  beforeDestroy() {
    if (this.timer) {
      clearInterval(this.timer);
    }
  }
}
</script>

<style lang="scss" scoped>
@import './auth.scss';

.send-captcha-btn {
  margin-right: -5px;
  min-width: 100px;
  height: 40px;
  line-height: 40px;
  border-radius: 4px;
  font-size: 14px;
  background: rgb(87, 120, 255);
  border: none;
  padding: 0px;

  &:disabled {
    background: #c0c4cc;
    cursor: not-allowed;
  }
}

// 人脸图片选择区域样式
.face-selection-section {
  margin: 20px 0;
  padding: 20px;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  background: #fafbfc;

  .section-title {
    display: flex;
    align-items: center;
    font-size: 16px;
    font-weight: 600;
    color: #303133;
    margin-bottom: 15px;

    i {
      margin-right: 8px;
      font-size: 18px;
      color: #5778ff;
    }
  }

  .face-search-box {
    display: flex;
    gap: 10px;
    margin-bottom: 15px;

    .face-search-input {
      flex: 1;
    }
  }
}

.face-images-container {
  .face-images-scroll {
    display: flex;
    gap: 12px;
    overflow-x: auto;
    padding: 10px 0;
    scroll-behavior: smooth;

    &::-webkit-scrollbar {
      height: 6px;
    }

    &::-webkit-scrollbar-track {
      background: #f1f1f1;
      border-radius: 3px;
    }

    &::-webkit-scrollbar-thumb {
      background: #c1c1c1;
      border-radius: 3px;

      &:hover {
        background: #a8a8a8;
      }
    }
  }

  .face-image-item {
    position: relative;
    flex-shrink: 0;
    width: 120px;
    height: 120px;
    border: 2px solid #e4e7ed;
    border-radius: 8px;
    overflow: hidden;
    cursor: pointer;
    transition: all 0.3s ease;
    background: white;

    &:hover {
      border-color: #5778ff;
      transform: translateY(-2px);
      box-shadow: 0 4px 12px rgba(87, 120, 255, 0.2);
    }

    &.selected {
      border-color: #5778ff;
      box-shadow: 0 0 0 2px rgba(87, 120, 255, 0.2);
    }

    img {
      width: 100%;
      height: 100%;
      object-fit: contain;
      background: #f5f7fa;
    }

    .image-overlay {
      position: absolute;
      top: 8px;
      right: 8px;
      width: 20px;
      height: 20px;
      background: rgba(87, 120, 255, 0.9);
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      opacity: 0;
      transition: opacity 0.3s ease;

      i {
        color: white;
        font-size: 12px;
      }
    }

    &.selected .image-overlay {
      opacity: 1;
    }

    .image-info {
      position: absolute;
      bottom: 0;
      left: 0;
      right: 0;
      background: linear-gradient(transparent, rgba(0, 0, 0, 0.8));
      color: white;
      padding: 6px 4px 3px;
      font-size: 10px;
      text-align: center;
      line-height: 1.2;

      span {
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        display: block;
      }
    }
  }

  .scroll-progress-container {
    margin: 15px 0 10px;

    .scroll-progress-bar {
      position: relative;
      height: 4px;
      background: #e4e7ed;
      border-radius: 2px;
      cursor: pointer;

      .scroll-progress-thumb {
        position: absolute;
        top: -2px;
        width: 8px;
        height: 8px;
        background: #5778ff;
        border-radius: 50%;
        cursor: grab;
        transition: transform 0.2s ease;

        &:hover {
          transform: scale(1.2);
        }

        &:active {
          cursor: grabbing;
        }
      }
    }
  }

  .selected-image-info {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 12px;
    background: #f0f9ff;
    border: 1px solid #b3d8ff;
    border-radius: 6px;
    font-size: 14px;
    color: #606266;

    .text-success {
      color: #67c23a;
    }
  }
}

.face-empty-state {
  text-align: center;
  padding: 40px 20px;
  color: #909399;

  i {
    font-size: 48px;
    color: #c0c4cc;
    margin-bottom: 16px;
    display: block;
  }

  p {
    margin: 8px 0;
    font-size: 14px;

    &.empty-tip {
      font-size: 12px;
      color: #c0c4cc;
    }
  }
}
</style>
