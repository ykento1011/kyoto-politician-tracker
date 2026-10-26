import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import fs from 'fs'
import path from 'path'
import { CITIES } from './src/config/cities.js'

function cloudflareMultiCityPlugin() {
  return {
    name: 'cloudflare-multi-city',
    closeBundle() {
      const distDir = path.resolve(process.cwd(), 'dist')
      const indexPath = path.join(distDir, 'index.html')

      if (!fs.existsSync(indexPath)) return

      const html = fs.readFileSync(indexPath, 'utf-8')

      // 404.html (SPA fallback)
      fs.writeFileSync(path.join(distDir, '404.html'), html, 'utf-8')

      // cities.js に定義されている active な都市ディレクトリと HTML を自動生成
      const generatedCities = []
      Object.values(CITIES).forEach((city) => {
        if (!city.active) return

        const targetDir = path.join(distDir, city.code)
        if (!fs.existsSync(targetDir)) {
          fs.mkdirSync(targetDir, { recursive: true })
        }

        const cityUrl = `https://gikai-mikata.jp/${city.code}/`
        const cityHtml = html
          .replace(/<title>.*?<\/title>/g, `<title>${city.title}</title>`)
          .replace(/<meta\s+name="description"\s+content=".*?"\s*\/?>/g, `<meta name="description" content="${city.description}" />`)
          .replace(/<link\s+rel="canonical"\s+href=".*?"\s*\/?>/g, `<link rel="canonical" href="${cityUrl}" />`)
          .replace(/<meta\s+property="og:url"\s+content=".*?"\s*\/?>/g, `<meta property="og:url" content="${cityUrl}" />`)
          .replace(/<meta\s+property="og:title"\s+content=".*?"\s*\/?>/g, `<meta property="og:title" content="${city.title}" />`)
          .replace(/<meta\s+property="og:description"\s+content=".*?"\s*\/?>/g, `<meta property="og:description" content="${city.description}" />`)
          .replace(/<meta\s+property="og:image"\s+content=".*?"\s*\/?>/g, `<meta property="og:image" content="${city.ogpImage}" />`)
          .replace(/<meta\s+name="twitter:title"\s+content=".*?"\s*\/?>/g, `<meta name="twitter:title" content="${city.title}" />`)
          .replace(/<meta\s+name="twitter:description"\s+content=".*?"\s*\/?>/g, `<meta name="twitter:description" content="${city.description}" />`)
          .replace(/<meta\s+name="twitter:image"\s+content=".*?"\s*\/?>/g, `<meta name="twitter:image" content="${city.ogpImage}" />`)

        fs.writeFileSync(path.join(targetDir, 'index.html'), cityHtml, 'utf-8')
        generatedCities.push(`dist/${city.code}/index.html`)
      })

      console.log(`✨ [Cloudflare Pages] ${generatedCities.join(', ')}, dist/404.html を自動生成しました。`)
    }
  }
}

export default defineConfig({
  base: '/',
  plugins: [react(), cloudflareMultiCityPlugin()],
})
