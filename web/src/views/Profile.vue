<template>
  <div class="profile-page">
    <el-card shadow="never" class="profile-card">
      <div class="profile-header">
        <div class="avatar-section">
          <div class="avatar-wrapper">
            <img :src="avatarUrl" alt="用户头像" class="avatar-img" />
            <label class="avatar-upload-btn">
              <input type="file" accept="image/jpeg,image/png,image/jpg" @change="handleAvatarChange" hidden />
              <el-icon class="upload-icon"><Camera /></el-icon>
            </label>
          </div>
          <p class="avatar-tip">点击头像上传（支持 jpg、png、jpeg 格式）</p>
        </div>
      </div>

      <el-divider />

      <div class="profile-info">
        <div class="info-header">
          <h3 class="info-title">个人信息</h3>
          <el-button type="primary" @click="showChangePassword = true">修改密码</el-button>
        </div>
        <el-form label-width="120px" class="info-form">
          <el-form-item label="用户ID">
            <el-input :value="userInfo.user_id || '-' " disabled />
          </el-form-item>
          <el-form-item label="用户名">
            <el-input :value="userInfo.username || '-' " disabled />
          </el-form-item>
          <el-form-item label="邮箱">
            <el-input :value="userInfo.email || '-' " disabled />
          </el-form-item>
          <el-form-item label="最后登录">
            <el-input :value="formatDate(userInfo.last_login_time) || '-' " disabled />
          </el-form-item>
        </el-form>
      </div>
    </el-card>

    <el-dialog title="修改密码" v-model="showChangePassword" width="400px" @close="resetPasswordForm">
      <el-form :model="passwordForm" :rules="passwordRules" ref="passwordFormRef" label-width="100px">
        <el-form-item label="原始密码" prop="oldPassword">
          <el-input v-model="passwordForm.oldPassword" type="password" />
        </el-form-item>
        <el-form-item label="新密码" prop="newPassword">
          <el-input v-model="passwordForm.newPassword" type="password" />
        </el-form-item>
        <el-form-item label="确认密码" prop="confirmPassword">
          <el-input v-model="passwordForm.confirmPassword" type="password" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showChangePassword = false">取消</el-button>
        <el-button type="primary" @click="handleChangePassword">确认修改</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { Camera } from '@element-plus/icons-vue'
import { getUserProfile, uploadAvatar, changePassword } from '../api'
import { ElMessage } from 'element-plus'

const userInfo = ref({})
const avatarUrl = ref('')
const showChangePassword = ref(false)
const passwordFormRef = ref(null)

const defaultAvatar = 'https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=user%20avatar%20placeholder%20icon%20simple%20circle%20silhouette&image_size=square'

const passwordForm = ref({
  oldPassword: '',
  newPassword: '',
  confirmPassword: '',
})

const passwordRules = {
  oldPassword: [
    { required: true, message: '请输入原始密码', trigger: 'blur' },
  ],
  newPassword: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 8, message: '密码长度不能少于8位', trigger: 'blur' },
    { pattern: /^(?=.*[a-z])(?=.*[A-Z])(?=.*[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>/?~`])/, message: '密码必须包含大小写英文字母和特殊符号', trigger: 'blur' },
  ],
  confirmPassword: [
    { required: true, message: '请确认新密码', trigger: 'blur' },
    { validator: (rule, value, callback) => {
      if (value !== passwordForm.value.newPassword) {
        callback(new Error('两次输入的密码不一致'))
      } else {
        callback()
      }
    }, trigger: 'blur' },
  ],
}

async function fetchProfile() {
  try {
    const res = await getUserProfile()
    userInfo.value = res.data || {}
    avatarUrl.value = userInfo.value.avator_url || defaultAvatar
  } catch (e) {
    ElMessage.error('获取用户信息失败')
    avatarUrl.value = defaultAvatar
  }
}

function handleAvatarChange(event) {
  const file = event.target.files[0]
  if (!file) return

  const validTypes = ['image/jpeg', 'image/png', 'image/jpg']
  if (!validTypes.includes(file.type)) {
    ElMessage.error('请选择 jpg、png 或 jpeg 格式的图片')
    return
  }

  uploadAvatar(file).then(() => {
    ElMessage.success('头像上传成功')
    fetchProfile()
  }).catch(() => {
    ElMessage.error('头像上传失败')
  })
}

function formatDate(str) {
  if (!str) return ''
  const d = new Date(str)
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function resetPasswordForm() {
  passwordForm.value = {
    oldPassword: '',
    newPassword: '',
    confirmPassword: '',
  }
  passwordFormRef.value?.resetFields()
}

async function handleChangePassword() {
  const valid = await passwordFormRef.value?.validate().catch(() => null)
  if (valid === null) return

  try {
    await changePassword(passwordForm.value.oldPassword, passwordForm.value.newPassword)
    ElMessage.success('密码修改成功')
    showChangePassword.value = false
    resetPasswordForm()
  } catch (e) {
    ElMessage.error(e.response?.data?.message || '密码修改失败')
  }
}

onMounted(fetchProfile)
</script>

<style scoped>
.profile-page {
  max-width: 600px;
  margin: 0 auto;
}

.profile-card {
  border-radius: 12px;
}

.profile-header {
  text-align: center;
  padding-bottom: 16px;
}

.avatar-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.avatar-wrapper {
  position: relative;
  width: 160px;
  height: 160px;
  border-radius: 50%;
  overflow: hidden;
  border: 4px solid #e4e7ed;
  cursor: pointer;
  transition: border-color 0.3s;
}

.avatar-wrapper:hover {
  border-color: #409eff;
}

.avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.avatar-upload-btn {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 40px;
  background: linear-gradient(to top, rgba(0, 0, 0, 0.7), transparent);
  display: flex;
  align-items: flex-end;
  justify-content: center;
  padding-bottom: 8px;
  opacity: 0;
  transition: opacity 0.3s;
  cursor: pointer;
}

.avatar-wrapper:hover .avatar-upload-btn {
  opacity: 1;
}

.upload-icon {
  color: #fff;
  font-size: 20px;
}

.avatar-tip {
  font-size: 12px;
  color: #909399;
  margin: 0;
}

.profile-info {
  padding-top: 16px;
}

.info-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.info-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  margin: 0;
}

.info-form {
  max-width: 400px;
}
</style>