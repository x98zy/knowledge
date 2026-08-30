<template>
  <div class="segment-detail-page">
    <!-- 顶部：返回 + 标题 -->
    <div class="page-header">
      <div class="header-title">
        <div class="breadcrumb">
          <el-button type="primary" link @click="goBack">
            <el-icon><ArrowLeft /></el-icon>
            {{ backButtonText }}
          </el-button>
        </div>
        <h2>分段详情</h2>
        <p class="header-desc">
          文件名：<span class="file-name">{{ displayFileName }}</span>
          &nbsp;·&nbsp;
          文件ID：<code>{{ fileId }}</code>
          &nbsp;·&nbsp;
          <el-tag size="small" type="info" effect="plain">共 {{ totalCount }} 个展示分段</el-tag>
        </p>
      </div>
    </div>

    <!-- 空状态 / 加载中 / 错误 -->
    <el-card shadow="never" class="segments-card" v-loading="loading">
      <!-- 异常提示 -->
      <el-alert
        v-if="errorText"
        :title="errorText"
        type="error"
        show-icon
        :closable="false"
        style="margin-bottom: 16px;"
      />
      <el-empty
        v-else-if="!loading && flatSegments.length === 0"
        description="当前文件还没有分段，等待解析成功后再来查看～"
        :image-size="120"
      />

      <!-- 分段列表（单层滚动容器，避免嵌套滚动，按经验 752439 避免多层滚动） -->
      <div v-else class="segments-list">
        <template v-for="(item, idx) in flatSegments" :key="item.key">
          <!-- 父分段标题（仅当它有子分段时出现：显示"子分段1/子分段2..."；当无子分段时作为普通分段渲染） -->
          <template v-if="item.kind === 'group'">
            <div class="group-header-row" :id="`group-${idx}`">
              <el-tag type="primary" effect="dark" class="group-tag">父分段 #{{ item.parentIndex }}</el-tag>
              <span class="group-title">
                该父分段下的子分段将分别展示，父分段原文不再重复渲染（有子不显示父）
                &nbsp;·&nbsp; position：{{ item.parentMeta.position ?? '-' }} &nbsp; id：<code>{{ item.parentMeta.id }}</code>
              </span>
            </div>

            <div
              v-for="(child, cIdx) in item.children"
              :key="child.id"
              class="segment-block child-block"
            >
              <div class="segment-meta">
                <el-tag size="small" type="warning" effect="light" class="segment-kind-tag">
                  子分段 {{ cIdx + 1 }}
                </el-tag>
                <span class="segment-sub-meta">
                  位置 position：{{ child.position ?? '-' }} &nbsp;·&nbsp; id：<code>{{ child.id }}</code>
                </span>
              </div>
              <div class="segment-content md-render" v-html="renderMarkdown(child.content)"></div>
            </div>
          </template>

          <!-- 无子分段：普通父分段（直接作为"分段 N"展示） -->
          <div v-else class="segment-block parent-standalone-block" :key="item.id">
            <div class="segment-meta">
              <el-tag size="small" type="success" effect="light" class="segment-kind-tag">
                分段 {{ item.parentIndex }}
              </el-tag>
              <span class="segment-sub-meta">
                位置 position：{{ item.position ?? '-' }} &nbsp;·&nbsp; id：<code>{{ item.id }}</code>
              </span>
            </div>
            <div class="segment-content md-render" v-html="renderMarkdown(item.content)"></div>
          </div>
        </template>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft } from '@element-plus/icons-vue'
import { marked } from 'marked'
import { getFileSegments } from '../../api'
import { ElMessage } from 'element-plus'

const props = defineProps({
  /** router props 注入：路由 params.fileId */
  fileId: {
    type: String,
    required: true,
  },
  /** router props 注入：路由 query.knowledge_id，用于返回到哪个知识库的文件列表 */
  knowledgeId: {
    type: String,
    default: '',
  },
})

const route = useRoute()
const router = useRouter()

// ---------------- marked 配置（基础 Markdown 即可，和 RAG Chat v1.1 保持同一版本） ----------------
marked.setOptions({
  gfm: true,
  breaks: false,
  headerIds: false,
  mangle: false,
})

function renderMarkdown(raw) {
  if (raw == null) return ''
  // 分段内容可能是 plain text（如 Excel 行、FAQ 对），对非 Markdown 文本需要换行能显示
  const text = String(raw).trim() ? String(raw) : '（空分段）'
  try {
    return marked.parse(text)
  } catch (e) {
    // 渲染失败兜底：原样显示（替换换行符为 <br/>）
    return String(text).replace(/[&<>]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c])).replace(/\n/g, '<br/>')
  }
}

// ---------------- 数据 ----------------
const loading = ref(false)
const errorText = ref('')
/** 原始后端返回 */
const rawSegments = ref([])

/**
 * 按需求扁平化（严格与后端返回字段对齐：id / content / position / child_segments）。
 *   - 若父分段含有子分段（child_segments.length > 0）：**不渲染父分段原文**，
 *     只渲染一条分组说明行，并在下面按 position 顺序渲染「子分段 1 / 子分段 2 / ...」。
 *   - 若父分段没有子分段：作为"分段 N"直接渲染其 content。
 *
 * 后端参考：
 *   api/service/file.py FileService.get_file_segments 返回 list[dict]，
 *   每一项 shape = { id, content, position, child_segments: [ {id, content, position} ] }。
 */
const flatSegments = computed(() => {
  const out = []
  const list = Array.isArray(rawSegments.value) ? rawSegments.value : []
  list.forEach((seg, i) => {
    if (!seg || typeof seg !== 'object') return
    const parentIndex = i + 1
    const children = Array.isArray(seg?.child_segments) ? seg.child_segments.filter(Boolean) : []
    if (children.length > 0) {
      out.push({
        kind: 'group',
        parentIndex,
        key: `g-${seg.id || i}`,
        // 父分段仅保留分组说明用的元信息；原文不显示（符合"有子不显示父"需求）
        parentMeta: {
          id: seg.id,
          position: seg.position,
        },
        children: children.map((c, ci) => ({
          id: c?.id ?? `child-${i}-${ci}`,
          position: c?.position ?? (ci + 1),
          content: c?.content == null ? '' : String(c.content),
        })),
      })
    } else {
      out.push({
        kind: 'segment',
        parentIndex,
        id: seg?.id ?? `seg-${i}`,
        position: seg?.position ?? (i + 1),
        content: seg?.content == null ? '' : String(seg.content),
        key: `s-${seg?.id || i}`,
      })
    }
  })
  return out
})

/** 用于顶栏统计的"展示分段数"（仅计数最终要渲染的块：独立分段 + 子分段） */
const totalCount = computed(() => {
  let n = 0
  for (const it of flatSegments.value) {
    if (it.kind === 'group') n += it.children.length
    else n += 1
  }
  return n
})

const displayFileName = computed(() => route.query.file_name || '未知文件名')

const backButtonText = computed(() => (props.knowledgeId ? '返回文件列表' : '返回知识库列表'))

// ---------------- 生命周期 ----------------
onMounted(async () => {
  if (!props.fileId) {
    errorText.value = '缺少 fileId 参数，无法加载分段'
    return
  }
  loading.value = true
  errorText.value = ''
  try {
    const data = await getFileSegments(props.fileId)
    rawSegments.value = Array.isArray(data) ? data : []
  } catch (e) {
    const msg = e.response?.data?.message || e.message || '加载分段失败'
    errorText.value = msg
    ElMessage.error(msg)
  } finally {
    loading.value = false
  }
})

// ---------------- 导航 ----------------
function goBack() {
  if (props.knowledgeId) {
    router.push({ name: 'KnowledgeFileList', params: { knowledgeId: props.knowledgeId } })
    return
  }
  router.push({ name: 'KnowledgeList' })
}
</script>

<style scoped>
.segment-detail-page {
  max-width: 1180px;
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
  line-height: 1.6;
}

.file-name {
  color: #303133;
  font-weight: 500;
  word-break: break-all;
}

.segments-card {
  border-radius: 8px;
}

/* 单层主滚动容器（遵循经验 752439：避免 dialog/table/cell 多级滚动） */
.segments-list {
  display: flex;
  flex-direction: column;
  gap: 18px;
  max-height: calc(100vh - 260px);
  overflow-y: auto;
  padding-right: 6px;
}

.group-header-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 2px 2px;
  margin-top: 10px;
  border-top: 1px dashed #ebeef5;
  padding-top: 14px;
}

.group-tag {
  flex-shrink: 0;
}

.group-title {
  color: #606266;
  font-size: 12.5px;
  line-height: 1.6;
}

.segment-block {
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 14px 16px;
  background: #fcfcfd;
}

.child-block {
  background: #fff;
  border-left: 3px solid #e6a23c;
}

.parent-standalone-block {
  border-left: 3px solid #67c23a;
}

.segment-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
  flex-wrap: wrap;
}

.segment-kind-tag {
  letter-spacing: 0.3px;
}

.segment-sub-meta {
  color: #909399;
  font-size: 12px;
}

.segment-sub-meta code {
  background: #f4f4f5;
  padding: 0 4px;
  border-radius: 3px;
  font-size: 11.5px;
  color: #606266;
}

/* Markdown 渲染样式，和 RAG Chat Chat.vue 保持同一观感，避免纯文本行无换行 */
.md-render {
  color: #303133;
  line-height: 1.75;
  font-size: 14px;
  word-break: break-word;
  white-space: normal;
}

.md-render :deep(h1),
.md-render :deep(h2),
.md-render :deep(h3),
.md-render :deep(h4) {
  margin: 14px 0 8px;
  font-weight: 600;
  color: #1f2329;
}

.md-render :deep(h1) { font-size: 18px; }
.md-render :deep(h2) { font-size: 16px; }
.md-render :deep(h3) { font-size: 15px; }
.md-render :deep(h4) { font-size: 14px; }

.md-render :deep(p) { margin: 6px 0; }

.md-render :deep(ul),
.md-render :deep(ol) {
  padding-left: 24px;
  margin: 6px 0;
}

.md-render :deep(li) {
  margin: 2px 0;
}

.md-render :deep(code) {
  background: #f4f4f5;
  padding: 1px 5px;
  border-radius: 4px;
  font-size: 12.5px;
  color: #d9001b;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}

.md-render :deep(pre) {
  background: #f6f8fa;
  border: 1px solid #ebeef5;
  border-radius: 6px;
  padding: 10px 12px;
  overflow-x: auto;
  margin: 8px 0;
}

.md-render :deep(pre code) {
  background: transparent;
  color: #1f2329;
  padding: 0;
}

.md-render :deep(table) {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  margin: 8px 0;
  overflow-x: auto;
  display: block;
}

.md-render :deep(th),
.md-render :deep(td) {
  border: 1px solid #ebeef5;
  padding: 6px 10px;
  text-align: left;
  vertical-align: top;
}

.md-render :deep(th) {
  background: #f5f7fa;
  font-weight: 600;
}

.md-render :deep(blockquote) {
  margin: 8px 0;
  padding: 4px 12px;
  border-left: 3px solid #dcdfe6;
  color: #606266;
  background: #fafafa;
}

.md-render :deep(a) {
  color: #409eff;
  text-decoration: none;
}
</style>
