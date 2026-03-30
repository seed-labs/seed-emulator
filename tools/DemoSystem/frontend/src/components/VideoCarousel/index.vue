<template>
  <div class="video-carousel-container">
    <el-carousel
        ref="carouselRef"
        :autoplay="false"
        :loop="true"
        arrow="always"
        indicator-position="none"
        height="600px"
        :initial-index="currentVideoIndex"
        @change="handleCarouselChange"
        @mouseenter="handleMouseEnter"
        @mouseleave="handleMouseLeave"
    >
      <el-carousel-item
          v-for="(video, index) in videoList"
          :key="index"
          :class="{ 'active-video': currentVideoIndex === index }"
      >
        <div class="video-item">
          <div class="video-container">
            <video
                ref="videoRefs"
                :data-index="index"
                :src="video.src"
                class="carousel-video"
                preload="metadata"
                :muted="isMuted"
                playsinline
                @loadedmetadata="handleVideoLoaded($event, index)"
                @ended="handleVideoEnded"
                @pause="handleVideoPause"
                @play="handleVideoPlay"
                @timeupdate="handleTimeUpdate"
            />

            <!-- 非激活状态的覆盖层 -->
            <div v-if="currentVideoIndex !== index" class="inactive-overlay" @click="switchToVideo(index)">
              <el-icon class="play-icon">
                <VideoPlay/>
              </el-icon>
              <div class="video-preview-info">
                <h4>{{ video.title }}</h4>
                <p>点击播放</p>
              </div>
            </div>

            <!-- 激活视频的控制层 -->
            <div v-if="currentVideoIndex === index" class="video-controls-layer">
              <!-- 视频信息 -->
              <div class="video-info-overlay">
                <h3 class="video-title">{{ video.title }}</h3>
                <p class="video-desc">{{ video.description }}</p>
              </div>

              <!-- 播放控制 -->
              <div class="video-play-controls">
                <div class="control-buttons">
                  <el-button
                      class="play-pause-btn"
                      type="primary"
                      :circle="true"
                      size="small"
                      @click="togglePlayPause"
                  >
                    <el-icon v-if="isVideoPlaying" size="16">
                      <VideoPause/>
                    </el-icon>
                    <el-icon v-else size="16">
                      <VideoPlay/>
                    </el-icon>
                  </el-button>

                  <div class="time-display">
                    {{ formatTime(currentTime) }} / {{ formatTime(duration) }}
                  </div>

                  <!-- 音量控制 -->
                  <div class="volume-control" v-show="!isMuted">
                    <el-slider
                        v-model="volume"
                        :max="1"
                        :step="0.1"
                        :show-tooltip="false"
                        height="4px"
                        @input="handleVolumeChange"
                    />
                  </div>

                  <!-- 全局声音控制按钮 -->
                  <el-button
                      class="global-sound-btn"
                      type="primary"
                      :circle="true"
                      size="small"
                      @click="toggleMute"
                  >
                    <el-icon v-if="isMuted" size="16">
                      <MuteNotification/>
                    </el-icon>
                    <el-icon v-else size="16">
                      <Bell/>
                    </el-icon>
                  </el-button>

                  <span class="sound-status">
                    {{ isMuted ? '静音' : Math.round(volume * 100) + '%' }}
                  </span>
                </div>
              </div>

              <!-- 可拖动进度条 -->
              <div
                  class="video-progress-container"
                  @mousedown="startProgressDrag"
                  @touchstart="startProgressDrag"
              >
                <div class="video-progress-background">
                  <div
                      class="video-progress-buffered"
                      :style="{ width: `${bufferedPercent}%` }"
                  ></div>
                  <div
                      class="video-progress-played"
                      :style="{ width: `${progressPercent}%` }"
                  ></div>
                  <div
                      class="video-progress-thumb"
                      :style="{ left: `${progressPercent}%` }"
                      @mousedown="startThumbDrag"
                      @touchstart="startThumbDrag"
                  ></div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </el-carousel-item>
    </el-carousel>
  </div>
</template>

<script setup lang="ts">
import {ref, onMounted, onUnmounted, nextTick, watch} from 'vue'
import {ElCarousel, ElCarouselItem, ElButton, ElIcon, ElSlider} from 'element-plus'
import {
  VideoPlay,
  VideoPause,
  Bell,
  MuteNotification
} from '@element-plus/icons-vue'

export interface VideoItem {
  src: string
  title: string
  description: string
}

const props = defineProps<{
  videos?: VideoItem[]
}>()

const defaultVideos: VideoItem[] = [
  {
    src: 'https://vjs.zencdn.net/v/oceans.mp4',
    title: '海洋世界',
    description: '探索神秘的海底世界，与海洋生物共舞'
  },
  {
    src: 'https://vjs.zencdn.net/v/oceans.mp4',
    title: '美丽风景',
    description: '欣赏大自然的壮丽景色，感受宁静与和谐'
  },
  {
    src: 'https://vjs.zencdn.net/v/oceans.mp4',
    title: '城市风光',
    description: '现代都市的繁华景象，快节奏的生活方式'
  },
  {
    src: 'https://vjs.zencdn.net/v/oceans.mp4',
    title: '科技未来',
    description: '前沿科技展示，感受未来生活的无限可能'
  },
  {
    src: 'https://vjs.zencdn.net/v/oceans.mp4',
    title: '自然奇观',
    description: '大自然的鬼斧神工，令人叹为观止'
  },
  {
    src: 'https://vjs.zencdn.net/v/oceans.mp4',
    title: '动物世界',
    description: '野生动物生活的精彩瞬间'
  },
  {
    src: 'https://vjs.zencdn.net/v/oceans.mp4',
    title: '人文历史',
    description: '探索人类文明的发展历程'
  },
  {
    src: 'https://vjs.zencdn.net/v/oceans.mp4',
    title: '太空探索',
    description: '宇宙的奥秘，星际的旅程'
  }
]

// 响应式数据
const videoList = ref<VideoItem[]>(props.videos || defaultVideos)
const carouselRef = ref<InstanceType<typeof ElCarousel> | null>(null)
const videoRefs = ref<HTMLVideoElement[]>([])
const isMuted = ref(true) // 默认静音，符合大多数自动播放要求
const currentVideoIndex = ref(0)
const isVideoPlaying = ref(false)
const volume = ref(1) // 音量，0-1之间
const currentTime = ref(0)
const duration = ref(0)
const progressPercent = ref(0)
const bufferedPercent = ref(0)

// 新增：控制视频播放结束后是否自动切换
const autoPlayNext = ref(true)

// 存储每个视频的播放状态
const videoPlaybackState = ref<Record<number, {
  currentTime: number
  isPlaying: boolean
}>>({})

// 进度条拖拽相关
const isDragging = ref(false)

// 切换视频
const switchToVideo = (index: number) => {
  if (carouselRef.value) {
    carouselRef.value.setActiveItem(index)
  }
}

// 鼠标进入轮播区域
const handleMouseEnter = () => {
  // 鼠标悬停时暂停自动切换
  autoPlayNext.value = false
}

// 鼠标离开轮播区域
const handleMouseLeave = () => {
  // 鼠标离开时恢复自动切换
  autoPlayNext.value = true
}

// 轮播切换时处理
const handleCarouselChange = (index: number) => {
  // 保存当前视频的播放状态
  saveCurrentVideoState()

  // 暂停所有视频
  pauseAllVideos()

  // 停止进度拖拽
  stopProgressDrag()

  // 更新当前视频索引
  currentVideoIndex.value = index

  // 重置进度数据
  currentTime.value = 0
  duration.value = 0
  progressPercent.value = 0
  bufferedPercent.value = 0

  // 播放新视频
  nextTick(() => {
    const newVideo = videoRefs.value[index]
    if (newVideo) {
      // 设置音量和静音状态
      newVideo.volume = volume.value
      newVideo.muted = isMuted.value

      // 加载视频时长
      if (newVideo.readyState >= 1) {
        duration.value = newVideo.duration || 0
      }

      // 恢复之前保存的播放位置（如果存在）
      const savedState = videoPlaybackState.value[index]
      if (savedState) {
        newVideo.currentTime = savedState.currentTime
        currentTime.value = savedState.currentTime
        progressPercent.value = (savedState.currentTime / (duration.value || 1)) * 100
      }

      // 播放视频
      playVideo(newVideo)
    }
  })
}

// 保存当前视频的播放状态
const saveCurrentVideoState = () => {
  const currentVideo = videoRefs.value[currentVideoIndex.value]
  if (currentVideo) {
    videoPlaybackState.value[currentVideoIndex.value] = {
      currentTime: currentVideo.currentTime,
      isPlaying: !currentVideo.paused
    }
  }
}

// 暂停所有视频
const pauseAllVideos = () => {
  videoRefs.value.forEach((video, index) => {
    if (video) {
      video.pause()
      // 更新播放状态
      if (videoPlaybackState.value[index]) {
        videoPlaybackState.value[index].isPlaying = false
      }
    }
  })
}

// 视频加载完成处理
const handleVideoLoaded = (event: Event, index: number) => {
  const video = event.target as HTMLVideoElement
  // 只设置当前激活视频的时长
  if (index === currentVideoIndex.value) {
    duration.value = video.duration || 0
  }

  // 如果这是第一个视频，自动播放
  if (index === 0 && currentVideoIndex.value === 0) {
    video.volume = volume.value
    video.muted = isMuted.value
    playVideo(video)
  }
}

// 视频时间更新事件
const handleTimeUpdate = (event: Event) => {
  const video = event.target as HTMLVideoElement
  const index = parseInt(video.dataset.index || '0')

  // 只更新当前激活视频的进度
  if (index === currentVideoIndex.value && !isDragging.value) {
    currentTime.value = video.currentTime
    progressPercent.value = (video.currentTime / (duration.value || 1)) * 100

    // 更新播放状态
    if (videoPlaybackState.value[index]) {
      videoPlaybackState.value[index].currentTime = video.currentTime
    }

    // 计算缓冲进度
    if (video.buffered.length > 0) {
      const bufferedEnd = video.buffered.end(video.buffered.length - 1)
      bufferedPercent.value = (bufferedEnd / (duration.value || 1)) * 100
    }
  }
}

// 视频播放结束处理 - 播放下一个视频（根据autoPlayNext决定）
const handleVideoEnded = () => {
  console.log('视频播放结束，autoPlayNext:', autoPlayNext.value)

  // 只有当前激活的视频结束时才切换，并且autoPlayNext为true
  if (autoPlayNext.value) {
    playNextVideo()
  } else {
    // 如果不自动切换，暂停当前视频并重置到开始
    const currentVideo = videoRefs.value[currentVideoIndex.value]
    if (currentVideo) {
      currentVideo.currentTime = 0
      currentVideo.pause()
      isVideoPlaying.value = false
    }
  }
}

// 视频暂停事件
const handleVideoPause = (event: Event) => {
  const video = event.target as HTMLVideoElement
  const index = parseInt(video.dataset.index || '0')

  // 只更新当前激活视频的播放状态
  if (index === currentVideoIndex.value) {
    isVideoPlaying.value = false
    // 更新播放状态
    if (videoPlaybackState.value[index]) {
      videoPlaybackState.value[index].isPlaying = false
    }
  }
}

// 视频播放事件
const handleVideoPlay = (event: Event) => {
  const video = event.target as HTMLVideoElement
  const index = parseInt(video.dataset.index || '0')

  // 只更新当前激活视频的播放状态
  if (index === currentVideoIndex.value) {
    isVideoPlaying.value = true
    // 更新播放状态
    if (videoPlaybackState.value[index]) {
      videoPlaybackState.value[index].isPlaying = true
    }
  }
}

// 播放视频
const playVideo = (video: HTMLVideoElement) => {
  const index = parseInt(video.dataset.index || '0')

  // 如果是非激活状态的视频，不播放
  if (index !== currentVideoIndex.value) {
    return
  }

  video.play()
      .then(() => {
        if (index === currentVideoIndex.value) {
          isVideoPlaying.value = true
          // 更新播放状态
          if (videoPlaybackState.value[index]) {
            videoPlaybackState.value[index].isPlaying = true
          }
        }
      })
      .catch(error => {
        console.log('视频播放失败:', error)
        if (index === currentVideoIndex.value) {
          isVideoPlaying.value = false
        }

        // 如果因为自动播放策略失败，尝试静音播放
        if (error.name === 'NotAllowedError') {
          video.muted = true
          isMuted.value = true
          video.play()
              .then(() => {
                if (index === currentVideoIndex.value) {
                  isVideoPlaying.value = true
                  // 更新播放状态
                  if (videoPlaybackState.value[index]) {
                    videoPlaybackState.value[index].isPlaying = true
                  }
                }
              })
              .catch(err => console.log('静音播放也失败:', err))
        }
      })
}

// 暂停当前视频
const pauseVideo = () => {
  const currentVideo = videoRefs.value[currentVideoIndex.value]
  if (currentVideo) {
    currentVideo.pause()
    isVideoPlaying.value = false
    // 更新播放状态
    if (videoPlaybackState.value[currentVideoIndex.value]) {
      videoPlaybackState.value[currentVideoIndex.value].isPlaying = false
    }
  }
}

// 切换播放/暂停状态
const togglePlayPause = () => {
  const currentVideo = videoRefs.value[currentVideoIndex.value]
  if (currentVideo) {
    if (currentVideo.paused) {
      playVideo(currentVideo)
    } else {
      pauseVideo()
    }
  }
}

// 切换静音状态
const toggleMute = () => {
  isMuted.value = !isMuted.value

  // 更新所有视频的静音状态
  videoRefs.value.forEach(video => {
    if (video) {
      video.muted = isMuted.value
      if (!isMuted.value) {
        video.volume = volume.value
      }
    }
  })
}

// 音量变化处理
const handleVolumeChange = (value: number) => {
  volume.value = value

  // 如果当前是静音状态，取消静音
  if (isMuted.value && value > 0) {
    isMuted.value = false
  }

  // 更新所有视频音量
  videoRefs.value.forEach(video => {
    if (video) {
      video.volume = value
      video.muted = isMuted.value
    }
  })
}

// 开始进度条拖拽
const startProgressDrag = (event: MouseEvent | TouchEvent) => {
  event.preventDefault()
  event.stopPropagation()
  isDragging.value = true

  const progressContainer = (event.currentTarget as HTMLElement)
  const rect = progressContainer.getBoundingClientRect()

  // 计算点击位置
  let clientX: number
  if (event instanceof MouseEvent) {
    clientX = event.clientX
  } else {
    clientX = event.touches[0].clientX
  }

  // 计算点击的进度百分比
  const clickX = clientX - rect.left
  const clickPercent = (clickX / rect.width) * 100

  // 设置新的播放位置
  setVideoProgress(clickPercent)

  // 添加全局拖拽监听
  document.addEventListener('mousemove', handleProgressDrag)
  document.addEventListener('touchmove', handleProgressDrag)
  document.addEventListener('mouseup', stopProgressDrag)
  document.addEventListener('touchend', stopProgressDrag)
}

// 开始滑块拖拽
const startThumbDrag = (event: MouseEvent | TouchEvent) => {
  event.stopPropagation()
  startProgressDrag(event)
}

// 处理进度条拖拽
const handleProgressDrag = (event: MouseEvent | TouchEvent) => {
  if (!isDragging.value) return

  event.preventDefault()
  event.stopPropagation()

  const progressContainer = document.querySelector('.video-progress-container') as HTMLElement
  if (!progressContainer) return

  const rect = progressContainer.getBoundingClientRect()

  // 计算当前位置
  let clientX: number
  if (event instanceof MouseEvent) {
    clientX = event.clientX
  } else {
    clientX = event.touches[0].clientX
  }

  // 计算进度百分比
  let clickX = clientX - rect.left
  clickX = Math.max(0, Math.min(clickX, rect.width))
  const clickPercent = (clickX / rect.width) * 100

  // 设置新的播放位置
  setVideoProgress(clickPercent)
}

// 停止进度条拖拽
const stopProgressDrag = () => {
  if (!isDragging.value) return

  isDragging.value = false

  // 移除全局拖拽监听
  document.removeEventListener('mousemove', handleProgressDrag)
  document.removeEventListener('touchmove', handleProgressDrag)
  document.removeEventListener('mouseup', stopProgressDrag)
  document.removeEventListener('touchend', stopProgressDrag)
}

// 设置视频进度
const setVideoProgress = (percent: number) => {
  const currentVideo = videoRefs.value[currentVideoIndex.value]
  if (!currentVideo || duration.value <= 0) return

  // 计算新的时间
  const newTime = (percent / 100) * duration.value

  // 更新视频当前时间
  currentVideo.currentTime = newTime

  // 更新显示
  currentTime.value = newTime
  progressPercent.value = percent

  // 更新播放状态
  if (videoPlaybackState.value[currentVideoIndex.value]) {
    videoPlaybackState.value[currentVideoIndex.value].currentTime = newTime
  }
}

// 播放下一个视频
const playNextVideo = () => {
  if (carouselRef.value) {
    const nextIndex = (currentVideoIndex.value + 1) % videoList.value.length
    carouselRef.value.setActiveItem(nextIndex)
  }
}

// 格式化时间显示 (秒 -> MM:SS)
const formatTime = (seconds: number): string => {
  if (isNaN(seconds) || seconds < 0) {
    return '00:00'
  }

  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)

  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
}

// 监听当前视频索引变化
watch(currentVideoIndex, () => {
  // 当视频切换时，重置进度数据
  currentTime.value = 0
  duration.value = 0
  progressPercent.value = 0
  bufferedPercent.value = 0
})

// 初始化
onMounted(() => {
  // 初始化播放状态
  videoList.value.forEach((_, index) => {
    videoPlaybackState.value[index] = {
      currentTime: 0,
      isPlaying: false
    }
  })

  // 等待DOM更新后播放第一个视频
  nextTick(() => {
    if (videoRefs.value.length > 0) {
      const firstVideo = videoRefs.value[0]
      if (firstVideo) {
        // 设置初始音量和静音状态
        firstVideo.volume = volume.value
        firstVideo.muted = isMuted.value
        playVideo(firstVideo)
      }
    }
  })
})

// 组件卸载时清理
onUnmounted(() => {
  // 停止进度拖拽
  stopProgressDrag()

  // 暂停所有视频
  videoRefs.value.forEach(video => {
    if (video) {
      video.pause()
    }
  })
})
</script>

<style scoped>
.video-carousel-container {
  width: 100%;
  margin: 0 auto;
  max-width: 1600px;
  background-color: #f5f7fa;
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

:deep(.el-carousel) {
  padding: 20px 0;
  width: 100%;
}

:deep(.el-carousel__container) {
  height: 500px !important;
}

:deep(.el-carousel__item) {
  transition: transform 0.4s ease, opacity 0.4s ease;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  position: absolute !important;
  transform: translateX(100%);
}


:deep(.el-carousel__item.is-active) {
  z-index: 2;
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.2);
}

:deep(.el-carousel__item:not(.is-active)) {
  opacity: 0.7;
  z-index: 1;
  transform: scale(1);
}

:deep(.el-carousel__item--card) {
  width: 60%;
}

.video-item {
  width: 100%;
  height: 100% !important;
  display: flex;
  align-items: stretch;
}

.video-container {
  position: relative;
  width: 100%;
  height: 100% !important;
  overflow: hidden;
  border-radius: 12px;
  background-color: #000;
  flex: 1;
}

.carousel-video {
  width: 100%;
  height: 100% !important;
  object-fit: contain;
  display: block;
  position: absolute;
  top: 0;
  left: 0;
}

.inactive-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.7);
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  color: white;
  cursor: pointer;
  transition: background-color 0.3s ease;
  z-index: 1;
}

.inactive-overlay:hover {
  background-color: rgba(0, 0, 0, 0.6);
}

.play-icon {
  font-size: 48px;
  margin-bottom: 15px;
  opacity: 0.8;
}

.video-preview-info {
  text-align: center;
}

.video-preview-info h4 {
  margin: 0 0 8px 0;
  font-size: 1.2rem;
}

.video-preview-info p {
  margin: 0;
  font-size: 0.9rem;
  opacity: 0.8;
}

.video-controls-layer {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  background: linear-gradient(
      to top,
      rgba(0, 0, 0, 0.8) 0%,
      rgba(0, 0, 0, 0.5) 30%,
      rgba(0, 0, 0, 0) 50%
  );
  pointer-events: none;
  z-index: 2;
}

.video-info-overlay {
  padding: 20px;
  color: white;
  pointer-events: none;
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
}

.video-title {
  margin: 0 0 8px 0;
  font-size: 1.3rem;
  font-weight: 600;
}

.video-desc {
  margin: 0;
  font-size: 0.85rem;
  opacity: 0.9;
  max-width: 70%;
}

.video-play-controls {
  padding: 10px 20px;
  background-color: rgba(0, 0, 0, 0.6);
  pointer-events: auto;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.control-buttons {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  flex-wrap: wrap;
}

.play-pause-btn, .global-sound-btn {
  background-color: rgba(255, 255, 255, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.3);
  transition: all 0.3s ease;
  flex-shrink: 0;
}

.play-pause-btn:hover, .global-sound-btn:hover {
  background-color: rgba(255, 255, 255, 0.3);
  transform: scale(1.05);
}

.time-display {
  font-size: 0.85rem;
  color: rgba(255, 255, 255, 0.9);
  white-space: nowrap;
  margin-left: auto;
}

.volume-control {
  width: 100px;
  flex-shrink: 0;
}

.sound-status {
  font-size: 0.85rem;
  color: rgba(255, 255, 255, 0.9);
  background-color: rgba(0, 0, 0, 0.4);
  padding: 4px 10px;
  border-radius: 10px;
  white-space: nowrap;
}

.video-progress-container {
  height: 40px;
  cursor: pointer;
  padding: 0 10px;
  display: flex;
  align-items: center;
  background-color: rgba(0, 0, 0, 0.6);
  pointer-events: auto;
}

.video-progress-background {
  position: relative;
  width: 100%;
  height: 4px;
  background-color: rgba(255, 255, 255, 0.3);
  border-radius: 2px;
  overflow: hidden;
}

.video-progress-buffered {
  position: absolute;
  top: 0;
  left: 0;
  height: 100%;
  background-color: rgba(255, 255, 255, 0.2);
  border-radius: 2px;
  transition: width 0.2s ease;
}

.video-progress-played {
  position: absolute;
  top: 0;
  left: 0;
  height: 100%;
  background-color: #409eff;
  border-radius: 2px;
  z-index: 2;
  transition: width 0.1s linear;
}

.video-progress-thumb {
  position: absolute;
  top: 50%;
  transform: translate(-50%, -50%);
  width: 12px;
  height: 12px;
  background-color: #409eff;
  border-radius: 50%;
  z-index: 3;
  cursor: pointer;
  box-shadow: 0 0 5px rgba(0, 0, 0, 0.5);
  transition: all 0.1s ease;
}

.video-progress-thumb:hover {
  width: 14px;
  height: 14px;
  background-color: #79bbff;
}

.video-progress-container:hover .video-progress-thumb {
  opacity: 1;
}

.video-progress-container:hover .video-progress-background {
  height: 6px;
}
</style>