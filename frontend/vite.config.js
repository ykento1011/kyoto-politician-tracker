import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import fs from 'fs'
import path from 'path'

// ビルド完了時に SPA 用の 404.html、/kyoto/index.html、/osaka/index.html を本番成果物から自動生成
function cloudflareMultiCityPlugin() {
  return {
    name: 'cloudflare-multi-city-spa',
    closeBundle() {
      const distDir = path.resolve(__dirname, 'dist')
      const indexPath = path.join(distDir, 'index.html')
      if (!fs.existsSync(indexPath)) return

      const html = fs.readFileSync(indexPath, 'utf-8')

      // 1. SPAフォールバック用の dist/404.html
      fs.writeFileSync(path.join(distDir, '404.html'), html, 'utf-8')

      // 2. /kyoto/ 直アクセス用の dist/kyoto/index.html
      const kyotoDir = path.join(distDir, 'kyoto')
      if (!fs.existsSync(kyotoDir)) {
        fs.mkdirSync(kyotoDir, { recursive: true })
      }
      const kyotoHtml = html
        .replace(/<title>.*?<\/title>/g, '<title>議会のミカタ 京都 ｜ AIは入口。判断するのは市民です。<\/title>')
        .replace(/<link\s+rel="canonical"\s+href=".*?"\s*\/?>/g, '<link rel="canonical" href="https://gikai-mikata.jp/kyoto/" />')
        .replace(/<meta\s+property="og:url"\s+content=".*?"\s*\/?>/g, '<meta property="og:url" content="https://gikai-mikata.jp/kyoto/" />')
      fs.writeFileSync(path.join(kyotoDir, 'index.html'), kyotoHtml, 'utf-8')

      // 3. /osaka/ 直アクセス用の dist/osaka/index.html
      const osakaDir = path.join(distDir, 'osaka')
      if (!fs.existsSync(osakaDir)) {
        fs.mkdirSync(osakaDir, { recursive: true })
      }
      const osakaHtml = html
        .replace(/<title>.*?<\/title>/g, '<title>議会のミカタ 大阪 ｜ AIは入口。判断するのは市民です。<\/title>')
        .replace(/京都市会\s*議員活動・賛否トラッカー/g, '大阪市会 議員活動・賛否トラッカー')
        .replace(/京都市政/g, '大阪市政')
        .replace(/京都市会/g, '大阪市会')
        .replace(/<link\s+rel="canonical"\s+href=".*?"\s*\/?>/g, '<link rel="canonical" href="https://gikai-mikata.jp/osaka/" />')
        .replace(/<meta\s+property="og:url"\s+content=".*?"\s*\/?>/g, '<meta property="og:url" content="https://gikai-mikata.jp/osaka/" />')
        .replace(/<meta\s+property="og:image"\s+content=".*?"\s*\/?>/g, '<meta property="og:image" content="https://gikai-mikata.jp/ogp-osaka.png" />')
        .replace(/<meta\s+name="twitter:image"\s+content=".*?"\s*\/?>/g, '<meta name="twitter:image" content="https://gikai-mikata.jp/ogp-osaka.png" />')
      fs.writeFileSync(path.join(osakaDir, 'index.html'), osakaHtml, 'utf-8')

      console.log('✨ [Cloudflare Pages] dist/kyoto/index.html, dist/osaka/index.html, dist/404.html を自動生成しました。')
    }
  }
}

export default defineConfig({
  base: '/',
  plugins: [react(), cloudflareMultiCityPlugin()],
})
