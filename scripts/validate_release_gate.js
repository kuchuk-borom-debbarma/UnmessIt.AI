import fs from 'node:fs'
import { execFileSync } from 'node:child_process'

const baseRef = process.env.RELEASE_BASE_REF || process.argv[2] || 'origin/staging'
const packagePath = 'web/package.json'
const changelogDir = 'changelog'

function fail(message) {
  console.error(`release gate failed: ${message}`)
  process.exit(1)
}

function git(args) {
  return execFileSync('git', args, { encoding: 'utf8' }).trim()
}

function versionOf(packageJson) {
  const version = JSON.parse(packageJson).version
  if (!/^\d+\.\d+\.\d+$/.test(version)) fail(`web/package.json version must be x.y.z, got ${version}`)
  return version
}

function newerThan(current, previous) {
  const a = current.split('.').map(Number)
  const b = previous.split('.').map(Number)
  for (let i = 0; i < 3; i += 1) {
    if (a[i] > b[i]) return true
    if (a[i] < b[i]) return false
  }
  return false
}

const changedFiles = git(['diff', '--name-only', `${baseRef}...HEAD`]).split('\n').filter(Boolean)

const isDocsOnly = changedFiles.length > 0 && changedFiles.every(file => file.endsWith('.md'))

if (isDocsOnly) {
  console.log(`release gate passed: docs-only changes detected. Bypassing version bump requirement.`)
  process.exit(0)
}

const currentVersion = versionOf(fs.readFileSync(packagePath, 'utf8'))
const currentChangelogPath = `${changelogDir}/${currentVersion}.md`
let previousVersion = '0.0.0'
try {
  previousVersion = versionOf(git(['show', `${baseRef}:${packagePath}`]))
} catch {
  console.warn(`release gate warning: could not read ${packagePath} from ${baseRef}; using ${previousVersion}`)
}

if (!newerThan(currentVersion, previousVersion)) {
  fail(`web/package.json version ${currentVersion} must be greater than ${previousVersion}`)
}

if (!changedFiles.includes(currentChangelogPath)) fail(`${currentChangelogPath} must be changed`)

if (!fs.existsSync(currentChangelogPath)) fail(`${currentChangelogPath} must exist`)

const notes = fs.readFileSync(currentChangelogPath, 'utf8').trim()
if (!notes || /No release notes found/i.test(notes) || !new RegExp(`^##\\s+\\[?${currentVersion}\\]?`, 'm').test(notes)) {
  fail(`${currentChangelogPath} needs release notes headed by ${currentVersion}`)
}

console.log(`release gate passed: ${previousVersion} -> ${currentVersion}`)
