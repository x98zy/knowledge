<template>
  <el-container class="app-layout">
    <!-- Sidebar -->
    <el-aside :width="isCollapse ? '64px' : '200px'" class="app-sidebar">
      <div class="sidebar-logo" @click="$router.push('/')">
        <span class="logo-icon">📚</span>
        <span v-show="!isCollapse" class="logo-text">个人知识库</span>
      </div>

      <el-menu
        :default-active="activeMenu"
        :collapse="isCollapse"
        :collapse-transition="false"
        router
        background-color="#304156"
        text-color="#bfcbd9"
        active-text-color="#409eff"
      >
        <el-menu-item index="/knowledge">
          <el-icon><Collection /></el-icon>
          <template #title>知识库</template>
        </el-menu-item>
        <el-menu-item index="/profile">
          <el-icon><User /></el-icon>
          <template #title>个人信息</template>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <!-- Main area -->
    <el-container>
      <!-- Header -->
      <el-header class="app-header">
        <div class="header-left">
          <el-icon class="collapse-btn" @click="isCollapse = !isCollapse">
            <Fold v-if="!isCollapse" />
            <Expand v-else />
          </el-icon>
        </div>
        <div class="header-right">
          <el-dropdown trigger="click">
            <span class="user-info">
              <img :src="avatarUrl" alt="头像" class="user-avatar" />
              <span class="username">{{ username }}</span>
              <el-icon><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="handleLogout">
                  <el-icon><SwitchButton /></el-icon>
                  退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <!-- Content -->
      <el-main class="app-main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import {
  Collection,
  Fold,
  Expand,
  UserFilled,
  User,
  ArrowDown,
  SwitchButton,
} from '@element-plus/icons-vue'
import { getUserProfile } from '../api'

const route = useRoute()
const isCollapse = ref(false)
const username = computed(() => localStorage.getItem('username') || '用户')
const avatarUrl = ref('')

const defaultAvatar = 'https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=user%20avatar%20placeholder%20icon%20simple%20circle%20silhouette&image_size=square'

const activeMenu = computed(() => route.path)

async function fetchAvatar() {
  try {
    const res = await getUserProfile()
    avatarUrl.value = res.data?.avator_url || defaultAvatar
  } catch {
    avatarUrl.value = defaultAvatar
  }
}

function handleLogout() {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
  localStorage.removeItem('username')
  window.location.hash = '#/login'
}

onMounted(fetchAvatar)
</script>

<style scoped>
.app-layout {
  height: 100vh;
}

.app-sidebar {
  background-color: #304156;
  overflow-x: hidden;
  transition: width 0.3s;
}

.sidebar-logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  cursor: pointer;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.logo-icon {
  font-size: 24px;
}

.logo-text {
  color: #fff;
  font-size: 16px;
  font-weight: 600;
  white-space: nowrap;
}

.el-menu {
  border-right: none;
}

.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
  padding: 0 20px;
  height: 60px;
}

.collapse-btn {
  font-size: 20px;
  cursor: pointer;
  color: #606266;
}

.collapse-btn:hover {
  color: #409eff;
}

.header-right {
  display: flex;
  align-items: center;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  color: #606266;
  font-size: 14px;
}

.user-info:hover {
  color: #409eff;
}

.user-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  object-fit: cover;
  border: 1px solid #e4e7ed;
}

.app-main {
  background: #f0f2f5;
  padding: 20px;
  overflow-y: auto;
}
</style>
