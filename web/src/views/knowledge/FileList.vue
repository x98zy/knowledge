<template>
  <div class="knowledge-file-list">
    <!-- 页面标题与操作 -->
    <div class="page-header">
      <div class="header-title">
        <div class="breadcrumb">
          <el-button type="primary" link @click="goBack">
            <el-icon><ArrowLeft /></el-icon>
            返回知识库列表
          </el-button>
        </div>
        <h2>文件列表</h2>
        <p class="header-desc">知识库「{{ knowledgeId }}」的文件管理</p>
      </div>
      <div class="header-actions">
        <el-button type="success" @click="openSearchDialog">
          <el-icon><Search /></el-icon>
          检索
        </el-button>
        <el-button type="primary" @click="showUploadDialog = true">
          <el-icon><Upload /></el-icon>
          上传知识文件
        </el-button>
      </div>
    </div>

    <!-- 搜索 -->
    <div class="search-bar">
      <el-input
        v-model="keyword"
        placeholder="搜索文件名称..."
        clearable
        @clear="handleSearch"
        @keyup.enter="handleSearch"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>
    </div>

    <!-- 列表 -->
    <el-card shadow="never" class="list-card">
      <el-table
        v-loading="loading"
        :data="tableData"
        stripe
        style="width: 100%"
        empty-text="暂无文件"
      >
        <el-table-column prop="id" label="文件ID" min-width="220" show-overflow-tooltip />
        <el-table-column prop="file_name" label="文件名称" min-width="200" show-overflow-tooltip />
        <el-table-column prop="created_time" label="创建时间" width="180" />
        <el-table-column prop="updated_time" label="更新时间" width="180" />
        <el-table-column prop="status" label="解析状态" width="120">
          <template #default="{ row }">
            <el-tag :type="getStatusTagType(row.status)" size="small">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="failed_reason" label="失败原因" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.failed_reason" :title="row.failed_reason">
              {{ row.failed_reason }}
            </span>
            <span v-else style="color: #c0c4cc;">-</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button
              type="primary"
              link
              size="small"
              :disabled="row.status !== 'success'"
              @click="goSegmentDetail(row)"
            >
              <el-icon style="vertical-align: -2px;"><List /></el-icon>
              分段详情
            </el-button>
            <el-divider direction="vertical" />
            <el-button
              type="danger"
              link
              size="small"
              :loading="row._deleting"
              @click="handleDelete(row)"
            >
              <el-icon style="vertical-align: -2px;"><Delete /></el-icon>
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-wrap" v-if="totalItems > 0">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 30, 50]"
          :total="totalItems"
          layout="total, sizes, prev, pager, next, jumper"
          background
          @size-change="handlePageChange"
          @current-change="handlePageChange"
        />
      </div>
    </el-card>

    <!-- 上传知识文件对话框 -->
    <el-dialog
      v-model="showUploadDialog"
      title="上传知识文件"
      width="600px"
      :close-on-click-modal="false"
      @closed="resetUploadForm"
    >
      <el-form
        ref="uploadFormRef"
        :model="uploadForm"
        :rules="uploadRules"
        label-width="120px"
        label-position="left"
      >
        <!-- 文件选择 -->
        <el-form-item label="选择文件" prop="file">
          <el-upload
            :auto-upload="false"
            :limit="1"
            :on-change="handleFileChange"
            :on-exceed="handleExceed"
            :on-remove="handleFileRemove"
            :file-list="fileList"
          >
            <el-button type="primary" :loading="fileUploading">
              <el-icon><Upload /></el-icon>
              {{ fileUploading ? '上传中...' : '选择文件' }}
            </el-button>
            <template #tip>
              <div class="el-upload__tip">支持 txt, md, pdf, docx, csv, xlsx, html 等格式（选择后将自动上传到 OSS）</div>
            </template>
          </el-upload>
        </el-form-item>

        <!-- 智能分段开关 -->
        <el-form-item label="智能分段" prop="enable_semantic">
          <el-switch v-model="uploadForm.enable_semantic" />
          <span class="semantic-tip">开启后由大模型自动进行语义分割，无需配置分段模式与规则</span>
        </el-form-item>

        <!-- 以下分段配置在开启智能分段时隐藏 -->
        <template v-if="!uploadForm.enable_semantic">
          <!-- 分段模式 -->
          <el-form-item label="分段模式" prop="segment_mode">
            <el-select v-model="uploadForm.segment_mode" placeholder="请选择分段模式" style="width: 100%">
              <el-option label="通用分段" value="text_model" />
              <el-option label="QA分段" value="qa_model" />
              <el-option label="父子分段" value="hierarchical_model" />
            </el-select>
          </el-form-item>

          <!-- 预处理规则（多选） -->
          <el-form-item label="预处理规则" prop="pre_rule">
            <el-checkbox-group v-model="uploadForm.pre_rule_list">
              <el-checkbox label="remove_urls_emails">去除URL链接</el-checkbox>
              <el-checkbox label="remove_extra_spaces">去除多余空格</el-checkbox>
            </el-checkbox-group>
          </el-form-item>

          <!-- 分段最大长度 -->
          <el-form-item label="分段最大长度" prop="max_tokens">
            <el-input-number v-model="uploadForm.max_tokens" :min="1" :max="10000" />
          </el-form-item>

          <!-- 分段重叠长度 -->
          <el-form-item label="分段重叠长度" prop="overlap">
            <el-input-number v-model="uploadForm.overlap" :min="0" :max="1000" />
          </el-form-item>

          <!-- 分段分隔符 -->
          <el-form-item label="分段分隔符" prop="delimiter">
            <el-input v-model="uploadForm.delimiter" placeholder="如 \n\n" />
          </el-form-item>

          <!-- 以下字段仅在「父子分段」时显示 -->
          <template v-if="uploadForm.segment_mode === 'hierarchical_model'">
            <el-divider>父子分段配置</el-divider>
            <el-form-item label="父分段规则" prop="parent_mode">
              <el-select v-model="uploadForm.parent_mode" placeholder="请选择父分段规则" style="width: 100%">
                <el-option label="全文" value="full-doc" />
                <el-option label="段落" value="paragraph" />
              </el-select>
            </el-form-item>
            <el-form-item label="子分段分隔符" prop="child_delimiter">
              <el-input v-model="uploadForm.child_delimiter" placeholder="如 \n" />
            </el-form-item>
            <el-form-item label="子分段重叠长度" prop="child_overlap">
              <el-input-number v-model="uploadForm.child_overlap" :min="0" :max="1000" />
            </el-form-item>
            <el-form-item label="子分段最大长度" prop="child_max_tokens">
              <el-input-number v-model="uploadForm.child_max_tokens" :min="1" :max="10000" />
            </el-form-item>
          </template>
        </template>
      </el-form>
      <template #footer>
        <el-button @click="showUploadDialog = false">取消</el-button>
        <el-button type="primary" :loading="uploading" @click="handleUpload">确定上传</el-button>
      </template>
    </el-dialog>

    <!-- 检索测试对话框 -->
    <el-dialog
      v-model="showSearchDialog"
      title="检索测试"
      width="720px"
      :close-on-click-modal="false"
      top="6vh"
    >
      <el-form :model="searchForm" label-width="100px" label-position="left">
        <el-form-item label="检索语句">
          <el-input
            v-model="searchForm.query"
            type="textarea"
            :rows="3"
            placeholder="输入要检索的 query"
          />
        </el-form-item>
        <el-form-item label="检索方式">
          <el-radio-group v-model="searchForm.method">
            <el-radio-button value="vector">向量检索</el-radio-button>
            <el-radio-button value="full-text">全文检索</el-radio-button>
            <el-radio-button value="hybrid">混合检索</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="Top K">
          <el-input-number v-model="searchForm.top_k" :min="1" :max="50" />
        </el-form-item>
        <el-form-item label="分数阈值">
          <el-input-number
            v-model="searchForm.score"
            :min="0"
            :max="1"
            :step="0.05"
            :precision="2"
          />
          <span class="search-tip">向量/混合检索为余弦相似度（0~1）；全文检索为 BM25 原始分，可填 0 不过滤</span>
        </el-form-item>
        <el-form-item label="重排模型">
          <el-select v-model="searchForm.rerankKey" placeholder="不使用重排" clearable style="width: 320px">
            <el-option
              v-for="m in rerankModelOptions"
              :key="`${m.provider}:${m.model}`"
              :label="`${m.model} (${m.provider})`"
              :value="`${m.provider}:${m.model}`"
            />
          </el-select>
        </el-form-item>
      </el-form>

      <!-- 检索结果 -->
      <div v-if="searchResults !== null" class="search-result">
        <el-divider content-position="left">
          检索结果（{{ searchResults.length }} 条）
        </el-divider>
        <el-empty v-if="searchResults.length === 0" description="未检索到分段，可适当降低分数阈值" :image-size="80" />
        <div v-else class="search-result-list">
          <div v-for="(doc, idx) in searchResults" :key="doc.id || idx" class="result-card">
            <div class="result-card-header">
              <span class="result-index">{{ idx + 1 }}</span>
              <el-tag size="small" type="success">score: {{ formatScore(doc.score) }}</el-tag>
              <el-tag v-if="doc.rerank_score != null" size="small" type="warning">
                rerank: {{ formatScore(doc.rerank_score) }}
              </el-tag>
            </div>
            <div class="result-content">{{ doc.page_content }}</div>
            <div v-if="doc.metadata && Object.keys(doc.metadata).length" class="result-meta">
              <el-tag
                v-for="(val, key) in doc.metadata"
                :key="key"
                size="small"
                type="info"
                effect="plain"
                class="meta-tag"
              >{{ key }}: {{ val }}</el-tag>
            </div>
          </div>
        </div>
      </div>

      <template #footer>
        <el-button @click="showSearchDialog = false">关闭</el-button>
        <el-button type="primary" :loading="searching" @click="handleSearchTest">开始检索</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, Search, Upload, Delete, List } from '@element-plus/icons-vue'
import {
  getKnowledgeFileList, uploadFile, createKnowledgeFile, deleteKnowledgeFile,
  searchKnowledge, getRerankModels,
} from '../../api'
import { ElMessage, ElMessageBox } from 'element-plus'

const route = useRoute()
const router = useRouter()

const knowledgeId = route.params.knowledgeId

// ---------- List state ----------
const loading = ref(false)
const tableData = ref([])
const keyword = ref('')
const currentPage = ref(1)
const pageSize = ref(10)
const totalItems = ref(0)

// ---------- Upload state ----------
const showUploadDialog = ref(false)
const uploading = ref(false)
const fileUploading = ref(false)
const uploadedFileKey = ref('')
const uploadFormRef = ref(null)
const fileList = ref([])

const uploadForm = reactive({
  file: null,
  enable_semantic: false,
  segment_mode: 'text_model',
  pre_rule_list: [],
  max_tokens: 500,
  overlap: 50,
  delimiter: '\\n\\n',
  parent_mode: '',
  child_delimiter: '',
  child_overlap: 0,
  child_max_tokens: 200,
})

// 校验规则动态化：开启智能分段时只校验文件，分段规则字段被 v-if 移除不参与校验
const uploadRules = computed(() => {
  if (uploadForm.enable_semantic) {
    return {
      file: [{ required: true, message: '请选择文件', trigger: 'change' }],
    }
  }
  return {
    file: [{ required: true, message: '请选择文件', trigger: 'change' }],
    segment_mode: [{ required: true, message: '请选择分段模式', trigger: 'change' }],
    max_tokens: [{ required: true, message: '请输入分段最大长度', trigger: 'blur' }],
    overlap: [{ required: true, message: '请输入分段重叠长度', trigger: 'blur' }],
    delimiter: [{ required: true, message: '请输入分段分隔符', trigger: 'blur' }],
    parent_mode: [{ required: true, message: '请选择父分段规则', trigger: 'change' }],
  }
})

// ---------- Search test state ----------
const showSearchDialog = ref(false)
const searching = ref(false)
const searchResults = ref(null)
const rerankModelOptions = ref([])
const searchForm = reactive({
  query: '',
  method: 'vector',
  top_k: 5,
  score: 0.5,
  rerankKey: '',
})

// ---------- Methods ----------
async function fetchList() {
  loading.value = true
  try {
    const res = await getKnowledgeFileList(knowledgeId, {
      page: currentPage.value,
      page_size: pageSize.value,
      keyword: keyword.value || undefined,
    })
    const page = res.data
    tableData.value = page.items || []
    totalItems.value = page.total_items || 0
  } catch (e) {
    ElMessage.error(e.response?.data?.message || '获取文件列表失败')
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  currentPage.value = 1
  fetchList()
}

function handlePageChange() {
  fetchList()
}

function goBack() {
  router.push({ name: 'KnowledgeList' })
}

/** 跳转到分段详情：携带 knowledge_id 方便点返回按钮回到该文件列表页 */
function goSegmentDetail(row) {
  router.push({
    name: 'KnowledgeFileSegments',
    params: { fileId: row.id },
    query: { knowledge_id: knowledgeId, file_name: row.file_name },
  })
}

// ---------- Search test handlers ----------
async function openSearchDialog() {
  showSearchDialog.value = true
  // 首次打开才拉取重排模型列表，避免每次点击都打接口
  if (rerankModelOptions.value.length === 0) {
    try {
      const res = await getRerankModels()
      rerankModelOptions.value = res.data?.models || []
    } catch {
      rerankModelOptions.value = []
    }
  }
}

function formatScore(value) {
  if (value == null) return '-'
  return Number(value).toFixed(4)
}

async function handleSearchTest() {
  const query = searchForm.query.trim()
  if (!query) {
    ElMessage.warning('请输入检索语句')
    return
  }

  // 解析重排模型选择："provider:model" → 两个字段；未选择则不传
  let rerankModel = null
  let rerankModelProvider = null
  if (searchForm.rerankKey) {
    const sepIndex = searchForm.rerankKey.indexOf(':')
    rerankModelProvider = searchForm.rerankKey.slice(0, sepIndex)
    rerankModel = searchForm.rerankKey.slice(sepIndex + 1)
  }

  searching.value = true
  try {
    searchResults.value = await searchKnowledge(searchForm.method, {
      query,
      top_k: searchForm.top_k,
      score: searchForm.score,
      dataset_ids: [knowledgeId],
      query_filter: {},
      rerank_model: rerankModel,
      rerank_model_provider: rerankModelProvider,
    })
  } catch (e) {
    searchResults.value = null
    ElMessage.error(e.response?.data?.message || '检索失败，请稍后重试')
  } finally {
    searching.value = false
  }
}

// ---------- Upload handlers ----------
async function handleFileChange(file) {
  uploadForm.file = file.raw
  fileList.value = [file]
  uploadedFileKey.value = ''

  if (!file.raw) return

  fileUploading.value = true
  try {
    const formData = new FormData()
    formData.append('file', file.raw)
    const uploadRes = await uploadFile(formData)
    uploadedFileKey.value = uploadRes.data.file_key
    ElMessage.success('文件已上传到 OSS')
  } catch (e) {
    ElMessage.error(e.response?.data?.message || '文件上传到 OSS 失败，请重新选择')
    // 清空选择，避免带着失败状态点确定
    fileList.value = []
    uploadForm.file = null
    uploadedFileKey.value = ''
  } finally {
    fileUploading.value = false
  }
}

function handleFileRemove() {
  uploadForm.file = null
  uploadedFileKey.value = ''
}

function handleExceed(files) {
  ElMessage.warning('只能上传一个文件，请先移除已选文件')
}

function resetUploadForm() {
  uploadFormRef.value?.resetFields()
  uploadForm.file = null
  fileList.value = []
  uploadedFileKey.value = ''
  fileUploading.value = false
  uploadForm.enable_semantic = false
  uploadForm.segment_mode = 'text_model'
  uploadForm.pre_rule_list = []
  uploadForm.max_tokens = 500
  uploadForm.overlap = 50
  uploadForm.delimiter = '\\n\\n'
  uploadForm.parent_mode = ''
  uploadForm.child_delimiter = ''
  uploadForm.child_overlap = 0
  uploadForm.child_max_tokens = 200
}

async function handleUpload() {
  const valid = await uploadFormRef.value?.validate().catch(() => null)
  if (valid === null) return

  if (!uploadedFileKey.value) {
    ElMessage.warning(fileUploading.value ? '文件仍在上传中，请稍候' : '请先选择并上传文件')
    return
  }

  uploading.value = true
  try {
    // 1. 组装请求体：开启智能分段时传 semantic_model，规则字段省略由后端默认值兜底落 ProcessRule
    const payload = {
      dataset_id: knowledgeId,
      file_key: uploadedFileKey.value,
      enable_semantic: uploadForm.enable_semantic,
      segment_mode: uploadForm.enable_semantic ? 'semantic_model' : uploadForm.segment_mode,
    }
    if (!uploadForm.enable_semantic) {
      // 拼接 pre_rule（多选用分号分隔）
      payload.pre_rule = uploadForm.pre_rule_list.join(';')
      payload.max_tokens = uploadForm.max_tokens
      payload.overlap = uploadForm.overlap
      payload.delimiter = uploadForm.delimiter
      const isHierarchical = uploadForm.segment_mode === 'hierarchical_model'
      payload.parent_mode = isHierarchical ? uploadForm.parent_mode : null
      payload.child_delimiter = isHierarchical ? uploadForm.child_delimiter : null
      payload.child_overlap = isHierarchical ? uploadForm.child_overlap : null
      payload.child_max_tokens = isHierarchical ? uploadForm.child_max_tokens : null
    }

    // 2. 创建文件记录，触发解析（使用已经上传 OSS 返回的 file_key）
    await createKnowledgeFile(payload)

    // 3. 成功提示并刷新列表
    ElMessage.success('文件上传成功，正在解析中...')
    showUploadDialog.value = false
    fetchList()
  } catch (e) {
    ElMessage.error(e.response?.data?.message || '创建文件记录失败')
  } finally {
    uploading.value = false
  }
}

function getStatusTagType(status) {
  const map = {
    waiting: 'info',
    processing: 'warning',
    indexing: 'warning',
    success: 'success',
    failed: 'danger',
  }
  return map[status] || 'info'
}

function getStatusText(status) {
  const map = {
    waiting: '等待解析',
    processing: '解析中',
    indexing: '索引中',
    success: '解析完成',
    failed: '解析失败',
  }
  return map[status] || status
}

// ---------- Delete handlers ----------
async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(
      `确定要删除文件「${row.file_name}」吗？该文件的分段与向量索引也将一并清理，操作不可恢复。`,
      '删除确认',
      {
        confirmButtonText: '确认删除',
        cancelButtonText: '取消',
        type: 'warning',
        confirmButtonClass: 'el-button--danger',
      }
    )
  } catch {
    return
  }

  try {
    row._deleting = true
    await deleteKnowledgeFile(row.id)
    ElMessage.success('删除成功，文件已移入后台清理')
    // 若当前页删光了（只剩这一条），优先切到前一页，避免空页
    if (tableData.value.length === 1 && currentPage.value > 1) {
      currentPage.value -= 1
    }
    fetchList()
  } catch (e) {
    ElMessage.error(e.response?.data?.message || '删除失败，请稍后重试')
  } finally {
    row._deleting = false
  }
}

onMounted(fetchList)
</script>

<style scoped>
.knowledge-file-list {
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 16px;
}

.breadcrumb {
  margin-bottom: 8px;
}

.page-header h2 {
  font-size: 22px;
  font-weight: 600;
  color: #303133;
  margin: 0;
}

.header-desc {
  color: #909399;
  font-size: 13px;
  margin: 4px 0 0 0;
}

.search-bar {
  margin-bottom: 16px;
  max-width: 360px;
}

.list-card {
  border-radius: 8px;
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

.semantic-tip {
  margin-left: 12px;
  color: #909399;
  font-size: 12px;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.search-tip {
  margin-left: 12px;
  color: #909399;
  font-size: 12px;
}

.search-result {
  max-height: 46vh;
  overflow-y: auto;
  padding-right: 4px;
}

.search-result-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.result-card {
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 10px 12px;
  background: #fafafa;
}

.result-card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.result-index {
  min-width: 22px;
  height: 22px;
  line-height: 22px;
  text-align: center;
  border-radius: 6px;
  background: #409eff;
  color: #fff;
  font-size: 12px;
  font-weight: 600;
}

.result-content {
  white-space: pre-wrap;
  word-break: break-word;
  color: #303133;
  font-size: 13px;
  line-height: 1.7;
}

.result-meta {
  margin-top: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.meta-tag {
  max-width: 100%;
}
</style>
