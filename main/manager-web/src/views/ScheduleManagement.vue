<template>
  <div class="welcome">
    <HeaderBar />

    <div class="operation-bar">
      <h2 class="page-title">日程管理</h2>
      <div class="right-operations">
        <el-button class="btn-add" @click="showAddDialog">
          <i class="el-icon-plus"></i>
          新增日程
        </el-button>
      </div>
    </div>

    <div class="main-wrapper">
      <div class="content-panel">
        <div class="content-area">
          <!-- 筛选条件 -->
          <div class="filter-section">
            <el-date-picker
              v-model="dateRange"
              type="daterange"
              range-separator="至"
              start-placeholder="开始日期"
              end-placeholder="结束日期"
              format="yyyy-MM-dd"
              value-format="yyyy-MM-dd"
              @change="handleDateChange">
            </el-date-picker>
            
            <el-select v-model="statusFilter" placeholder="状态筛选" @change="handleStatusChange">
              <el-option label="全部" value=""></el-option>
              <el-option label="未完成" value="0"></el-option>
              <el-option label="已完成" value="1"></el-option>
            </el-select>
            
            <el-input
              v-model="contentFilter"
              placeholder="搜索日程内容"
              class="search-input"
              @keyup.enter.native="handleSearch"
              clearable>
            </el-input>
            
            <el-button class="btn-search" @click="handleSearch">
              搜索
            </el-button>
          </div>

          <!-- 日程表格 -->
          <el-card class="schedule-card" shadow="never">
            <el-table
              ref="scheduleTable"
              :data="scheduleList"
              class="transparent-table"
              v-loading="loading"
              element-loading-text="拼命加载中"
              element-loading-spinner="el-icon-loading"
              element-loading-background="rgba(255, 255, 255, 0.7)">
              
              <el-table-column label="序号" type="index" width="60" align="center"></el-table-column>
              
              <el-table-column label="日程内容" prop="content" min-width="300">
                <template slot-scope="scope">
                  <div class="content-cell">
                    <span :class="{ 'completed-text': scope.row.status === 1 }">
                      {{ scope.row.content }}
                    </span>
                  </div>
                </template>
              </el-table-column>
              
              <el-table-column label="日程日期" prop="scheduleDate" width="120" align="center">
                <template slot-scope="scope">
                  {{ formatDate(scope.row.scheduleDate) }}
                </template>
              </el-table-column>
              
              <el-table-column label="状态" prop="status" width="100" align="center">
                <template slot-scope="scope">
                  <el-tag
                    :type="scope.row.status === 1 ? 'success' : 'warning'"
                    size="small">
                    {{ scope.row.status === 1 ? '已完成' : '未完成' }}
                  </el-tag>
                </template>
              </el-table-column>
              
              <el-table-column label="操作" width="280" align="center">
                <template slot-scope="scope">
                  <div class="operation-buttons">
                    <el-button
                      size="mini"
                      :type="scope.row.status === 1 ? 'warning' : 'success'"
                      @click="toggleStatus(scope.row)"
                      class="status-btn">
                      {{ scope.row.status === 1 ? '标记未完成' : '标记完成' }}
                    </el-button>
                    <el-button
                      size="mini"
                      type="primary"
                      @click="editSchedule(scope.row)">
                      编辑
                    </el-button>
                    <el-button
                      size="mini"
                      type="danger"
                      @click="deleteSchedule(scope.row)">
                      删除
                    </el-button>
                  </div>
                </template>
              </el-table-column>
            </el-table>

            <!-- 分页 -->
            <div class="pagination-container">
              <div class="pagination-wrapper">
                <el-select v-model="pageSize" @change="handlePageSizeChange" class="page-size-selector">
                  <el-option v-for="size in pageSizeOptions" :key="size" :label="`${size}条/页`" :value="size">
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
                <span class="total-text">共{{ total }}条记录</span>
              </div>
            </div>
          </el-card>
        </div>
      </div>
    </div>

    <!-- 新增/编辑日程对话框 -->
    <el-dialog
      :title="dialogMode === 'add' ? '新增日程' : '编辑日程'"
      :visible.sync="showDialog"
      width="500px"
      @close="resetForm">
      <el-form
        ref="scheduleForm"
        :model="scheduleForm"
        :rules="formRules"
        label-width="80px">
        <el-form-item label="日程内容" prop="content">
          <el-input
            v-model="scheduleForm.content"
            type="textarea"
            :rows="3"
            placeholder="请输入日程内容">
          </el-input>
        </el-form-item>
        <el-form-item label="日程日期" prop="scheduleDate">
          <el-date-picker
            v-model="scheduleForm.scheduleDate"
            type="date"
            placeholder="选择日期"
            format="yyyy-MM-dd"
            value-format="yyyy-MM-dd"
            style="width: 100%">
          </el-date-picker>
        </el-form-item>
        <el-form-item label="状态" prop="status" v-if="dialogMode === 'edit'">
          <el-select v-model="scheduleForm.status" placeholder="请选择状态" style="width: 100%">
            <el-option label="未完成" :value="0"></el-option>
            <el-option label="已完成" :value="1"></el-option>
          </el-select>
        </el-form-item>
      </el-form>
      <div slot="footer" class="dialog-footer">
        <el-button @click="showDialog = false">取消</el-button>
        <el-button type="primary" @click="saveSchedule" :loading="saving">确定</el-button>
      </div>
    </el-dialog>

    <el-footer>
      <version-footer />
    </el-footer>
  </div>
</template>

<script>
import Api from "@/apis/api";
import HeaderBar from "@/components/HeaderBar.vue";
import VersionFooter from "@/components/VersionFooter.vue";

export default {
  components: { HeaderBar, VersionFooter },
  data() {
    return {
      scheduleList: [],
      loading: false,
      saving: false,
      showDialog: false,
      dialogMode: 'add', // 'add' 或 'edit'
      
      // 筛选条件
      dateRange: null,
      statusFilter: '',
      contentFilter: '',
      
      // 分页
      currentPage: 1,
      pageSize: 10,
      total: 0,
      pageSizeOptions: [10, 20, 50, 100],
      
      // 表单
      scheduleForm: {
        id: null,
        content: '',
        scheduleDate: '',
        status: 0
      },
      formRules: {
        content: [
          { required: true, message: '请输入日程内容', trigger: 'blur' }
        ],
        scheduleDate: [
          { required: true, message: '请选择日程日期', trigger: 'change' }
        ]
      }
    };
  },
  computed: {
    pageCount() {
      return Math.ceil(this.total / this.pageSize);
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
  created() {
    this.fetchSchedules();
  },
  methods: {
    fetchSchedules() {
      this.loading = true;
      const params = {
        page: this.currentPage,
        limit: this.pageSize
      };
      
      if (this.dateRange && this.dateRange.length === 2) {
        params.startDate = this.dateRange[0];
        params.endDate = this.dateRange[1];
      }
      
      if (this.statusFilter !== '') {
        params.status = this.statusFilter;
      }
      
      if (this.contentFilter) {
        params.content = this.contentFilter;
      }

      Api.schedule.getSchedulePage(
        params,
        (response) => {
          if (response.data && response.data.code === 0) {
            this.scheduleList = response.data.data.list || [];
            this.total = response.data.data.total || 0;
          } else {
            this.$message.error(response.data?.msg || '获取日程列表失败');
          }
          this.loading = false;
        },
        (error) => {
          console.error('获取日程列表失败:', error);
          this.$message.error('获取日程列表失败');
          this.loading = false;
        },
        (error) => {
          console.error('网络错误:', error);
          this.$message.error('网络连接失败');
          this.loading = false;
        }
      );
    },
    
    showAddDialog() {
      this.dialogMode = 'add';
      this.showDialog = true;
    },
    
    editSchedule(row) {
      this.dialogMode = 'edit';
      this.scheduleForm = {
        id: row.id,
        content: row.content,
        scheduleDate: row.scheduleDate,
        status: row.status
      };
      this.showDialog = true;
    },
    
    saveSchedule() {
      this.$refs.scheduleForm.validate((valid) => {
        if (!valid) return;
        
        this.saving = true;
        if (this.dialogMode === 'add') {
          Api.schedule.addSchedule(
            this.scheduleForm,
            (response) => {
              if (response.data && response.data.code === 0) {
                this.$message.success('日程添加成功');
                this.showDialog = false;
                this.fetchSchedules();
              } else {
                this.$message.error(response.data?.msg || '操作失败');
              }
              this.saving = false;
            },
            (error) => {
              console.error('保存日程失败:', error);
              this.$message.error('保存日程失败');
              this.saving = false;
            },
            (error) => {
              console.error('网络错误:', error);
              this.$message.error('网络连接失败');
              this.saving = false;
            }
          );
        } else {
          Api.schedule.updateSchedule(
            this.scheduleForm,
            (response) => {
              if (response.data && response.data.code === 0) {
                this.$message.success('日程更新成功');
                this.showDialog = false;
                this.fetchSchedules();
              } else {
                this.$message.error(response.data?.msg || '操作失败');
              }
              this.saving = false;
            },
            (error) => {
              console.error('更新日程失败:', error);
              this.$message.error('更新日程失败');
              this.saving = false;
            },
            (error) => {
              console.error('网络错误:', error);
              this.$message.error('网络连接失败');
              this.saving = false;
            }
          );
        }
      });
    },
    
    toggleStatus(row) {
      const newStatus = row.status === 1 ? 0 : 1;
      Api.schedule.updateScheduleStatus(
        row.id,
        newStatus,
        (response) => {
          if (response.data && response.data.code === 0) {
            this.$message.success('状态更新成功');
            this.fetchSchedules();
          } else {
            this.$message.error(response.data?.msg || '状态更新失败');
          }
        },
        (error) => {
          console.error('更新状态失败:', error);
          this.$message.error('更新状态失败');
        },
        (error) => {
          console.error('网络错误:', error);
          this.$message.error('网络连接失败');
        }
      );
    },
    
    deleteSchedule(row) {
      this.$confirm(`确定要删除日程"${row.content}"吗？`, '提示', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }).then(() => {
        Api.schedule.deleteSchedule(
          row.id,
          (response) => {
            if (response.data && response.data.code === 0) {
              this.$message.success('日程删除成功');
              this.fetchSchedules();
            } else {
              this.$message.error(response.data?.msg || '删除失败');
            }
          },
          (error) => {
            console.error('删除日程失败:', error);
            this.$message.error('删除失败');
          },
          (error) => {
            console.error('网络错误:', error);
            this.$message.error('网络连接失败');
          }
        );
      });
    },
    
    resetForm() {
      this.scheduleForm = {
        id: null,
        content: '',
        scheduleDate: '',
        status: 0
      };
      this.$refs.scheduleForm && this.$refs.scheduleForm.resetFields();
    },
    
    handleDateChange() {
      this.currentPage = 1;
      this.fetchSchedules();
    },
    
    handleStatusChange() {
      this.currentPage = 1;
      this.fetchSchedules();
    },
    
    handleSearch() {
      this.currentPage = 1;
      this.fetchSchedules();
    },
    
    handlePageSizeChange() {
      this.currentPage = 1;
      this.fetchSchedules();
    },
    
    goFirst() {
      this.currentPage = 1;
      this.fetchSchedules();
    },
    
    goPrev() {
      if (this.currentPage > 1) {
        this.currentPage--;
        this.fetchSchedules();
      }
    },
    
    goNext() {
      if (this.currentPage < this.pageCount) {
        this.currentPage++;
        this.fetchSchedules();
      }
    },
    
    goToPage(page) {
      this.currentPage = page;
      this.fetchSchedules();
    },
    
    formatDate(date) {
      if (!date) return '';
      return new Date(date).toLocaleDateString('zh-CN');
    }
  }
};
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

.right-operations {
  display: flex;
  gap: 10px;
}

.btn-add {
  background: linear-gradient(135deg, #6b8cff, #a966ff);
  border: none;
  color: white;
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

.schedule-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.schedule-card :deep(.el-card__body) {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.transparent-table {
  flex: 1;
  background: transparent;
}

.content-cell {
  line-height: 1.4;
}

.completed-text {
  text-decoration: line-through;
  color: #909399;
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: center;
}

.pagination-wrapper {
  display: flex;
  align-items: center;
  gap: 8px;
}

.page-size-selector {
  width: 120px;
  margin-right: 16px;
}

.pagination-btn {
  padding: 8px 12px;
  border: 1px solid #dcdfe6;
  background: white;
  cursor: pointer;
  border-radius: 4px;
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

.dialog-footer {
  text-align: right;
}

:deep(.el-table) {
  .el-table__header {
    background: #f8f9fa;
  }
  
  .el-table__row:nth-child(even) {
    background: #fafafa;
  }
}

/* 确保操作按钮在一行显示 */
.el-table-column .el-button {
  margin: 0 2px;
}

/* 操作按钮容器样式 */
.operation-buttons {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 4px;
  white-space: nowrap;
}

.operation-buttons .el-button {
  margin: 0;
  height: 28px;
  line-height: 1;
  font-size: 12px;
  padding: 7px 15px;
}

/* 状态按钮特殊样式 */
.operation-buttons .status-btn {
  min-width: 78px;
}
</style>
