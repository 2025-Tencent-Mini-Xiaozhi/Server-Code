<template>
  <div class="welcome">
    <HeaderBar />

    <div class="operation-bar">
      <h2 class="page-title">人脸模块管理</h2>
    </div>

    <div class="main-wrapper">
      <div class="content-panel">
        <div class="content-area">
          <!-- 搜索区域 -->
          <div class="filter-section">
            <el-input
              v-model="searchDeviceId"
              placeholder="请输入设备码进行检索，如：2b_c8_58"
              class="search-input"
              @keyup.enter.native="handleSearch"
              clearable>
              <i slot="suffix" class="el-icon-search" @click="handleSearch"></i>
            </el-input>
            
            <el-button class="btn-search" @click="handleSearch">
              搜索
            </el-button>
            
            <el-button @click="handleReset">
              重置
            </el-button>
          </div>

          <!-- 人脸管理主体 -->
          <div class="face-management">
            <!-- 图片展示区域 -->
            <div class="image-container">
              <template v-if="isLoading">
                <div v-for="n in 10" :key="n" class="image-item skeleton">
                  <div class="image-placeholder"></div>
                  <div class="image-info">
                    <div class="info-line"></div>
                    <div class="info-line short"></div>
                  </div>
                </div>
              </template>
              <template v-else>
                <div 
                  v-for="image in paginatedImages" 
                  :key="image.name" 
                  class="image-item"
                >
                  <div class="image-wrapper">
                    <img 
                      :src="getImageUrl(image.name)" 
                      :alt="image.name"
                      @error="handleImageError"
                    />
                  </div>
                  <div class="image-info">
                    <div class="image-name" :title="image.name">{{ image.name }}</div>
                    <div class="image-meta">
                      <span>大小: {{ formatFileSize(image.size) }}</span>
                      <span>时间: {{ formatTimestamp(image.timestamp) }}</span>
                    </div>
                  </div>
                </div>
              </template>
              
              <!-- 空状态 -->
              <div v-if="!isLoading && images.length === 0" class="empty-state">
                <el-empty description="暂无图片数据"></el-empty>
              </div>
            </div>

            <!-- 分页 -->
            <div class="pagination-container" v-if="images.length > 0">
              <div class="pagination-wrapper">
                <el-select v-model="pageSize" @change="handlePageSizeChange" class="page-size-selector">
                  <el-option v-for="size in pageSizeOptions" :key="size" :label="size + '条/页'" :value="size">
                  </el-option>
                </el-select>

                <button class="pagination-btn" :disabled="currentPage === 1" @click="goFirst">
                  首页
                </button>
                <button class="pagination-btn" :disabled="currentPage === 1" @click="goPrev">
                  上一页
                </button>
                <button v-for="page in visiblePages" :key="page" class="pagination-btn"
                  :class="{ active: page === currentPage }" @click="goToPage(page)">
                  {{ page }}
                </button>
                <button class="pagination-btn" :disabled="currentPage === pageCount" @click="goNext">
                  下一页
                </button>
                <span class="total-text">共{{ images.length }}条记录</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import Api from '@/apis/api';
import HeaderBar from '@/components/HeaderBar.vue';

export default {
  name: 'FaceManagement',
  components: {
    HeaderBar
  },
  data() {
    return {
      images: [],
      currentPage: 1,
      pageSize: 10,
      pageSizeOptions: [10, 20, 50],
      searchDeviceId: '',
      isLoading: true,
      imageUrls: {} // 缓存图片blob URLs
    }
  },
  
  computed: {
    paginatedImages() {
      const start = (this.currentPage - 1) * this.pageSize;
      const end = start + this.pageSize;
      return this.images.slice(start, end); // 直接从 images 分页，不使用 filteredImages
    },
    
    pageCount() {
      return Math.ceil(this.images.length / this.pageSize);
    },
    
    visiblePages() {
      const pages = [];
      const maxVisible = 3;
      let start = Math.max(1, this.currentPage - 1);
      let end = Math.min(this.pageCount, start + maxVisible - 1);

      if (end - start < maxVisible - 1) {
        start = Math.max(1, end - maxVisible + 1);
      }

      for (let i = start; i <= end; i++) {
        pages.push(i);
      }
      return pages;
    }
  },
  
  mounted() {
    this.loadImages();
  },
  
  methods: {
    // 加载图片列表
    loadImages() {
      this.isLoading = true;
      Api.face.getFaceImages(
        (response) => {
          // 处理响应数据
          if (response.data.code === 0) {
            this.images = response.data.data.map(item => ({
              name: item.name,
              size: item.size,
              timestamp: item.timestamp || Math.floor(Date.now() / 1000)
            }));
            // 预加载图片
            this.preloadImages();
          } else {
            this.$message.error(response.data.msg || '获取图片列表失败');
            // 出错时使用模拟数据
            this.loadMockData();
          }
          this.isLoading = false;
        },
        (error) => {
          console.error('加载图片列表失败:', error);
          this.$message.error('加载图片列表失败: ' + (error.message || '未知错误'));
          // 出错时使用模拟数据
          this.loadMockData();
          this.isLoading = false;
        },
        this.searchDeviceId // 传递设备码参数
      );
    },
    
    // 加载模拟数据
    loadMockData() {
      const mockImages = [
        {
          name: 'camera_2b_c8_58_1756051233.jpg',
          size: 15100,
          timestamp: 1756051233
        },
        {
          name: 'camera_2b_c8_58_1756051236.jpg',
          size: 15200,
          timestamp: 1756051236
        },
        {
          name: 'camera_2b_c8_58_1756051239.jpg',
          size: 15000,
          timestamp: 1756051239
        },
        {
          name: 'camera_2b_c8_58_1756051242.jpg',
          size: 15000,
          timestamp: 1756051242
        },
        {
          name: 'camera_2b_c8_58_1756051245.jpg',
          size: 15100,
          timestamp: 1756051245
        },
        {
          name: 'camera_2b_c8_58_1756051248.jpg',
          size: 14000,
          timestamp: 1756051248
        },
        {
          name: 'camera_2b_c8_58_1756051251.jpg',
          size: 15900,
          timestamp: 1756051251
        },
        {
          name: 'camera_2b_c8_58_1756051254.jpg',
          size: 15900,
          timestamp: 1756051254
        },
        {
          name: 'camera_2b_c8_58_1756051257.jpg',
          size: 15200,
          timestamp: 1756051257
        },
        {
          name: 'camera_2b_c8_58_1756051260.jpg',
          size: 15000,
          timestamp: 1756051260
        }
      ];
      
      // 如果有搜索条件，过滤模拟数据
      if (this.searchDeviceId) {
        this.images = mockImages.filter(item => 
          item.name.toLowerCase().includes(this.searchDeviceId.toLowerCase())
        );
      } else {
        this.images = mockImages;
      }
      
      // 预加载图片
      this.preloadImages();
    },
    
    // 预加载图片
    preloadImages() {
      this.images.forEach(image => {
        this.loadImageAsBlob(image.name).then(blobUrl => {
          this.$set(this.imageUrls, image.name, blobUrl);
        }).catch(error => {
          console.warn(`Failed to load image ${image.name}:`, error);
          // 保持默认图片
        });
      });
    },
    
    // 加载图片为blob URL
    loadImageAsBlob(imageName) {
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
    
    // 获取图片URL
    getImageUrl(imageName) {
      return this.imageUrls[imageName] || require('@/assets/home/equipment.png');
    },
    
    // 处理图片加载错误
    handleImageError(event) {
      event.target.src = require('@/assets/home/equipment.png'); // 使用更通用的默认图片
    },
    
    // 格式化文件大小
    formatFileSize(size) {
      if (size < 1024) {
        return size + ' B';
      } else if (size < 1024 * 1024) {
        return (size / 1024).toFixed(2) + ' KB';
      } else {
        return (size / (1024 * 1024)).toFixed(2) + ' MB';
      }
    },
    
    // 格式化时间戳
    formatTimestamp(timestamp) {
      const date = new Date(timestamp * 1000);
      return date.toLocaleString('zh-CN');
    },
    
    // 处理搜索
    handleSearch() {
      this.currentPage = 1;
      this.loadImages(); // 重新加载数据，会传递当前的搜索设备码
    },
    
    // 重置搜索
    handleReset() {
      this.searchDeviceId = '';
      this.currentPage = 1;
      this.loadImages(); // 重新加载所有数据
    },
    
    // 处理分页变化
    handlePageChange(page) {
      this.currentPage = page;
      // 滚动到顶部
      window.scrollTo({ top: 0, behavior: 'smooth' });
    },
    
    // 处理每页大小变化
    handlePageSizeChange() {
      this.currentPage = 1;
    },
    
    // 跳转到首页
    goFirst() {
      this.currentPage = 1;
    },
    
    // 上一页
    goPrev() {
      if (this.currentPage > 1) {
        this.currentPage--;
      }
    },
    
    // 下一页
    goNext() {
      if (this.currentPage < this.pageCount) {
        this.currentPage++;
      }
    },
    
    // 跳转到指定页
    goToPage(page) {
      this.currentPage = page;
    }
  }
}
</script>

<style lang="scss" scoped>
.welcome {
  min-width: 900px;
  min-height: 506px;
  height: 100vh;
  display: flex;
  position: relative;
  flex-direction: column;
  box-sizing: border-box;
  background: linear-gradient(145deg, #e6eeff, #eff0ff);
  background-size: cover;
  background-position: center;
  -webkit-background-size: cover;
  -o-background-size: cover;
}

.operation-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
}

.page-title {
  font-size: 24px;
  margin: 0;
  color: #303133;
}

.main-wrapper {
  flex: 1;
  padding: 0 24px 24px;
  overflow: hidden;
}

.content-panel {
  height: 100%;
  border-radius: 15px;
  background: white;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  display: flex;
  flex-direction: column;
}

.content-area {
  flex: 1;
  padding: 24px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.filter-section {
  display: flex;
  gap: 16px;
  align-items: center;
  margin-bottom: 20px;
  flex-wrap: wrap;
}

.search-input {
  width: 240px;
}

.btn-search {
  background: linear-gradient(135deg, #6b8cff, #a966ff);
  border: none;
  color: white;
}

.face-management {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  
  .image-container {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 20px;
    margin-bottom: 20px;
    flex: 1;
    overflow-y: auto;
    
    @media (max-width: 1600px) {
      grid-template-columns: repeat(4, 1fr);
    }
    
    @media (max-width: 1200px) {
      grid-template-columns: repeat(3, 1fr);
    }
    
    @media (max-width: 768px) {
      grid-template-columns: repeat(2, 1fr);
    }
  }
  
  .image-item {
    border: 1px solid #ebeef5;
    border-radius: 4px;
    overflow: hidden;
    transition: all 0.3s;
    background: white;
    
    &:hover {
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
      transform: translateY(-2px);
    }
    
    .image-wrapper {
      width: 100%;
      height: 150px;
      display: flex;
      align-items: center;
      justify-content: center;
      background-color: #f5f7fa;
      
      img {
        max-width: 100%;
        max-height: 100%;
        object-fit: contain;
      }
    }
    
    .image-info {
      padding: 10px;
      
      .image-name {
        font-size: 14px;
        color: #606266;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        margin-bottom: 5px;
      }
      
      .image-meta {
        font-size: 12px;
        color: #909399;
        
        span {
          display: block;
          overflow: hidden;
          text-overflow: ellipsis;
        }
      }
    }
  }
  
  .skeleton {
    .image-placeholder {
      width: 100%;
      height: 150px;
      background: linear-gradient(90deg, #f0f2f5 25%, #e6e8eb 37%, #f0f2f5 63%);
      background-size: 400% 100%;
      animation: skeleton-loading 1.4s ease infinite;
    }
    
    .image-info {
      padding: 10px;
      
      .info-line {
        height: 16px;
        background: #f0f2f5;
        margin-bottom: 8px;
        border-radius: 2px;
        
        &.short {
          width: 70%;
        }
      }
    }
  }
  
  .empty-state {
    grid-column: 1 / -1;
    text-align: center;
    padding: 40px 0;
    color: #606266;
  }
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: center;
}

.pagination-wrapper {
  display: flex;
  align-items: center;
  gap: 10px;
}

.page-size-selector {
  width: 120px;
  margin-right: 20px;
}

.pagination-btn {
  padding: 8px 16px;
  border: 1px solid #dcdfe6;
  background: white;
  color: #606266;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.3s;

  &:hover:not(:disabled) {
    background: #f5f7fa;
    border-color: #c0c4cc;
  }

  &.active {
    background: #409eff;
    color: white;
    border-color: #409eff;
  }

  &:disabled {
    color: #c0c4cc;
    cursor: not-allowed;
    background: #f5f7fa;
  }
}

.total-text {
  margin-left: 16px;
  color: #606266;
  font-size: 14px;
}

@keyframes skeleton-loading {
  0% {
    background-position: 100% 50%;
  }
  100% {
    background-position: 0 50%;
  }
}
</style>
