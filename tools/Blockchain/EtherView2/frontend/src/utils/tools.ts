import {ElLoading} from "element-plus";

export const AllLoading = () => {
    // fullscreen:true 表示全屏遮罩
    return ElLoading.service({
        lock: true,                     // 锁定页面，防止交互
        text: '加载中…',                // 提示文字
        background: 'rgba(0,0,0,0.3)', // 背景透明度
        fullscreen: true               // 全屏模式
    })
}