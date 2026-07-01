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

// 2. Read the CHANGELOG.md
const changelogPath = path.join(rootDir, 'CHANGELOG.md')
const changelogContent = fs.readFileSync(changelogPath, 'utf8')

// 3. Extract all version sections, newest first.
const versionHeaderRegex = /^##\s+\[?(\d+\.\d+\.\d+)\]?.*$/gm
const matches = [...changelogContent.matchAll(versionHeaderRegex)]
const history = matches.map((match, index) => {
  const next = matches[index + 1]
  return {
    version: match[1],
    changelog: changelogContent.substring(match.index, next?.index).trim()
  }
})

const currentEntry = history.find((entry) => entry.version === currentVersion)
let releaseNotes = currentEntry?.changelog || ''

if (!releaseNotes) {
  console.warn(`⚠️ Warning: Could not find release notes for version ${currentVersion} in CHANGELOG.md`)
  releaseNotes = `## UnmessIt.AI ${currentVersion}\n\n*No release notes found in CHANGELOG.md.*`
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
