import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const rootDir = path.resolve(__dirname, '..')
const webDir = path.join(rootDir, 'web')

// 1. Get the current version from web/package.json
const packageJsonPath = path.join(webDir, 'package.json')
const packageJson = JSON.parse(fs.readFileSync(packageJsonPath, 'utf8'))
const currentVersion = packageJson.version

console.log(`Generating version.json for v${currentVersion}...`)

// 2. Read versioned changelog files in semver order.
const changelogDir = path.join(rootDir, 'changelog')
const semverRegex = /^(\d+)\.(\d+)\.(\d+)\.md$/
const history = fs.readdirSync(changelogDir)
  .filter((file) => semverRegex.test(file))
  .sort((a, b) => {
    const av = a.match(semverRegex).slice(1).map(Number)
    const bv = b.match(semverRegex).slice(1).map(Number)
    for (let i = 0; i < 3; i += 1) {
      if (av[i] !== bv[i]) return av[i] - bv[i]
    }
    return 0
  })
  .map((file) => ({
    version: file.replace(/\.md$/, ''),
    changelog: fs.readFileSync(path.join(changelogDir, file), 'utf8').trim()
  }))

const currentEntry = history.find((entry) => entry.version === currentVersion)
let releaseNotes = currentEntry?.changelog || ''

if (!releaseNotes) {
  console.warn(`⚠️ Warning: Could not find release notes for version ${currentVersion} in changelog/${currentVersion}.md`)
  releaseNotes = `## UnmessIt.AI ${currentVersion}\n\n*No release notes found in changelog/${currentVersion}.md.*`
}

// 4. Write to web/public/version.json
const outputData = {
  version: currentVersion,
  changelog: releaseNotes,
  history
}

const outputPath = path.join(webDir, 'public', 'version.json')
fs.writeFileSync(outputPath, JSON.stringify(outputData, null, 2))

console.log(`✅ Successfully generated ${outputPath}`)
