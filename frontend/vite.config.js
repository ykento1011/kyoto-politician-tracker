import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import fs from 'fs'
import path from 'path'
import { execSync } from 'child_process'
import { CITIES } from './src/config/cities.js'

function cloudflareMultiCityPlugin() {
  return {
    name: 'cloudflare-multi-city',
    async closeBundle() {
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

      // 全365議員の SSG (JSON-LD事前注入) & sitemap.xml 自動生成
      try {
        console.log('🚀 [SSG] 全365議員の構造化データ (JSON-LD) と sitemap.xml の生成を実行中...');
        execSync('python ../data-pipeline/generate_councilors_ssg.py', { stdio: 'inherit' });
      } catch (err) {
        console.error('⚠️ [SSG] generate_councilors_ssg.py 実行警告:', err.message);
      }

      console.log(`✨ [Cloudflare Pages] ${generatedCities.join(', ')}, dist/404.html を自動生成しました。`)
    }
  }
}

export default defineConfig({
  base: '/',
  plugins: [react(), cloudflareMultiCityPlugin()],
  build: {
    chunkSizeWarningLimit: 600,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('node_modules/react/') || id.includes('node_modules/react-dom/')) {
            return 'vendor-react';
          }
          if (id.includes('node_modules/recharts/')) {
            return 'vendor-charts';
          }
          if (id.includes('node_modules/lucide-react/')) {
            return 'vendor-icons';
          }
          if (id.includes('node_modules/minisearch/') || id.includes('node_modules/@supabase/')) {
            return 'vendor-core';
          }
        }
      }
    }
  }
})
