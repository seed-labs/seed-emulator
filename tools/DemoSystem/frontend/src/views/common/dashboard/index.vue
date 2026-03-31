<script setup lang="ts">
import Dashboard from "@/components/Dashboard/index.vue"
import type {GridItem} from "@/components/Dashboard/index.vue"
import type {VideoItem} from "@/components/VideoCarousel/index.vue"
import {menus} from "@/extensions";
import {findMenuByName} from "@/utils/tools.ts";

interface Props {
  dashboardName?: string
}

// 接收 Props
const props = withDefaults(defineProps<Props>(), {
  dashboardName: 'home'
})
const title = "网络仿真演示平台"
const dashboardKey = ref(0)
const cardTitle = ref(title)
const videoList = ref<VideoItem[]>([])
const gridList = ref<GridItem[]>([])

watch(
    () => props.dashboardName,
    async (newVal) => {
      newVal = newVal || 'home'
      dashboardKey.value++
      let menu = findMenuByName(menus, newVal)
      if (!menu) {
        menu = findMenuByName(menus, "home")!
      }
      cardTitle.value = `${title} - ${menu.meta.title}`
      const children = menu?.children
      if (newVal === "home") {
        gridList.value = menus.filter(item => item.name !== "home").map((item) => {
          return {
            name: item.name,
            img: item.meta.img,
            title: item.meta.title,
            description: item.meta.description,
            path: item.path,
          } as GridItem
        })
        return
      } else if (!children?.length) {
        gridList.value = []
        return
      }
      gridList.value = children.map((item) => {
        return {
          name: item.name,
          path: item.path,
          img: item.meta.img,
          title: item.meta.title,
          description: item.meta.description,
        } as GridItem
      })
    },
    {immediate: true}
)

</script>

<template>
  <Dashboard
      :key="dashboardKey"
      :title="cardTitle"
      :video-list="videoList"
      :grid-list="gridList"
  />

</template>

<style scoped>

</style>