<template>
  <div class="knowledge-list">
    <!-- 页面标题与操作 -->
    <div class="page-header">
      <div class="header-title">
        <h2>知识库</h2>
        <p class="header-desc">管理你的知识库文档集合</p>
      </div>
      <el-button type="primary" @click="showCreateDialog = true">
        <el-icon><Plus /></el-icon>
        创建知识库
      </el-button>
    </div>

    <!-- 搜索 -->
    <div class="search-bar">
      <el-input
        v-model="keyword"
        placeholder="搜索知识库名称或描述..."
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
        empty-text="暂无知识库"
      >
        <el-table-column prop="name" label="名称" min-width="180">
          <template #default="{ row }">
            <div class="kb-name kb-name-clickable" @click="goToFileList(row)">
              <span class="kb-icon">📚</span>
              <span>{{ row.name }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="280" show-overflow-tooltip />
        <el-table-column prop="embedding_model" label="嵌入模型" width="180" />
        <el-table-column prop="embedding_provider" label="模型提供方" width="140" />
        <el-table-column prop="created_time" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_time) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="goToFileList(row)">详情</el-button>
            <el-button type="danger" link size="small" :loading="deletingId === row.id" @click="handleDelete(row)">删除</el-button>
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

    <!-- 创建知识库弹窗 -->
    <el-dialog
      v-model="showCreateDialog"
      title="创建知识库"
      width="520px"
      :close-on-click-modal="false"
    >
      <el-form
        ref="createFormRef"
        :model="createForm"
        :rules="createRules"
        label-width="100px"
        label-position="left"
      >
        <el-form-item label="名称" prop="name">
          <el-input v-model="createForm.name" placeholder="请输入知识库名称" />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input
            v-model="createForm.description"
            type="textarea"
            :rows="3"
            placeholder="请输入知识库描述"
          />
        </el-form-item>
        <el-form-item label="嵌入模型" prop="embedding_model">
          <el-select
            v-model="createForm.embedding_model"
            placeholder="请选择嵌入模型"
            style="width: 100%"
            @focus="fetchEmbeddingModels"
          >
            <el-option
              v-for="m in embeddingModels"
              :key="`${m.provider}/${m.model}`"
              :label="`${m.model} (${m.provider})`"
              :value="m.model"
            />
          </el-select>
        </el-form-item>
        <!-- hidden provider, filled when model selected -->
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleCreate">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Plus, Search } from '@element-plus/icons-vue'
import { getKnowledgeList, createKnowledge, getEmbeddingModels, deleteKnowledge } from '../../api'
import { ElMessage, ElMessageBox } from 'element-plus'

const router = useRouter()

// ---------- Delete state ----------
const deletingId = ref('')

// ---------- List state ----------
const loading = ref(false)
const tableData = ref([])
const keyword = ref('')
const currentPage = ref(1)
const pageSize = ref(10)
const totalItems = ref(0)

// ---------- Create state ----------
const showCreateDialog = ref(false)
const submitting = ref(false)
const createFormRef = ref(null)
const embeddingModels = ref([])

const createForm = reactive({
  name: '',
  description: '',
  embedding_model: '',
})

const createRules = {
  name: [{ required: true, message: '请输入知识库名称', trigger: 'blur' }],
  embedding_model: [{ required: true, message: '请选择嵌入模型', trigger: 'change' }],
}

// ---------- Methods ----------
async function fetchList() {
  loading.value = true
  try {
    const res = await getKnowledgeList({
      page: currentPage.value,
      page_size: pageSize.value,
      keyword: keyword.value || undefined,
    })
    // Backend wraps in: { success, code, message, data: Page }
    const page = res.data
    tableData.value = page.items || []
    totalItems.value = page.total_items || 0
  } catch (e) {
    ElMessage.error(e.response?.data?.message || '获取知识库列表失败')
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

async function fetchEmbeddingModels() {
  if (embeddingModels.value.length > 0) return
  try {
    const res = await getEmbeddingModels()
    embeddingModels.value = res.data?.models || []
  } catch {
    // ignore
  }
}

async function handleCreate() {
  const valid = await createFormRef.value?.validate().catch(() => null)
  if (valid === null) return

  const model = embeddingModels.value.find((m) => m.model === createForm.embedding_model)
  submitting.value = true
  try {
    await createKnowledge({
      name: createForm.name,
      description: createForm.description,
      embedding_model: createForm.embedding_model,
      embedding_provider: model?.provider || '',
    })
    ElMessage.success('知识库创建成功')
    showCreateDialog.value = false
    createForm.name = ''
    createForm.description = ''
    createForm.embedding_model = ''
    fetchList()
  } catch (e) {
    ElMessage.error(e.response?.data?.message || '创建失败')
  } finally {
    submitting.value = false
  }
}

function formatDate(str) {
  if (!str) return '-'
  const d = new Date(str)
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function goToFileList(row) {
  router.push({ name: 'KnowledgeFileList', params: { knowledgeId: row.id } })
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(
      `确定要删除知识库「${row.name}」吗？该操作将同时删除其下所有文件与向量数据，且不可恢复。`,
      '删除知识库',
      {
        confirmButtonText: '确定删除',
        cancelButtonText: '取消',
        type: 'warning',
        confirmButtonClass: 'el-button--danger',
      }
    )
  } catch {
    // 用户点了取消
    return
  }

  deletingId.value = row.id
  try {
    const res = await deleteKnowledge(row.id)
    // 后端返回 { success, code, message, data }
    if (res?.success) {
      ElMessage.success(res?.message || '知识库正在进行后台异步删除')
      // 当前页如果只剩这一条，删除后回到上一页，避免空列表
      if (tableData.value.length === 1 && currentPage.value > 1) {
        currentPage.value -= 1
      }
      fetchList()
    } else {
      ElMessage.error(res?.message || '删除失败')
    }
  } catch (e) {
    ElMessage.error(e.response?.data?.message || '删除失败')
  } finally {
    deletingId.value = ''
  }
}

onMounted(fetchList)
</script>

<style scoped>
.knowledge-list {
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 16px;
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

.kb-name {
  display: flex;
  align-items: center;
  gap: 8px;
}

.kb-name-clickable {
  cursor: pointer;
  color: #409eff;
}

.kb-name-clickable:hover {
  text-decoration: underline;
}

.kb-icon {
  font-size: 18px;
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
