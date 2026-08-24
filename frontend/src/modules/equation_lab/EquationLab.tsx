import { useState, type FormEvent } from 'react'

import { balanceEquation } from './api'
import type { BalanceEquationResponse, EquationMode } from './types'
import './equation-lab.css'


interface EquationLabProps {
  onBack: () => void
}

interface EquationLabViewProps extends EquationLabProps {
  onBalance: (
    equation: string,
    mode: EquationMode,
  ) => Promise<BalanceEquationResponse>
}

const EXAMPLES: Array<{
  label: string
  equation: string
  mode: EquationMode
}> = [
  { label: '水的生成', equation: 'H2 + O2 -> H2O', mode: 'molecular' },
  {
    label: '沉淀示例',
    equation: 'Ag+(aq) + Cl-(aq) -> AgCl(s)',
    mode: 'net_ionic',
  },
  {
    label: '无净反应示例',
    equation: 'Na+(aq) + NO3-(aq)',
    mode: 'net_ionic',
  },
]

const MODE_LABELS: Record<EquationMode, string> = {
  molecular: '分子方程式',
  ionic: '离子方程式',
  net_ionic: '净离子方程式',
}

export function EquationLabView({ onBack, onBalance }: EquationLabViewProps) {
  const [equation, setEquation] = useState(EXAMPLES[0].equation)
  const [mode, setMode] = useState<EquationMode>(EXAMPLES[0].mode)
  const [result, setResult] = useState<BalanceEquationResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      setResult(await onBalance(equation, mode))
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '方程式处理失败')
    } finally {
      setLoading(false)
    }
  }

  const chooseExample = (example: (typeof EXAMPLES)[number]) => {
    setEquation(example.equation)
    setMode(example.mode)
    setResult(null)
    setError(null)
  }

  return (
    <main className="equation-lab-page">
      <nav className="lab-breadcrumb" aria-label="面包屑导航">
        <button type="button" onClick={onBack}>元素周期表</button>
        <span aria-hidden="true">/</span>
        <span>方程实验室</span>
      </nav>

      <header className="lab-hero">
        <div>
          <p className="eyebrow">M05 · Equation Lab</p>
          <h1>方程实验室</h1>
          <p>使用精确整数运算配平方程式，并逐项核对元素与适用时的总电荷守恒。</p>
        </div>
        <div className="lab-principle">
          <span>A · x = 0</span>
          <strong>最简正整数比</strong>
        </div>
      </header>

      <div className="lab-layout">
        <section className="lab-panel lab-input" aria-labelledby="input-heading">
          <div className="lab-heading">
            <div><p className="eyebrow">Equation</p><h2 id="input-heading">输入方程式</h2></div>
            <span>离子电荷可写作 Ag+、SO4^2-</span>
          </div>
          <div className="lab-examples" aria-label="方程式示例">
            {EXAMPLES.map((example) => (
              <button key={example.label} type="button" onClick={() => chooseExample(example)}>
                {example.label}
              </button>
            ))}
          </div>
          <form onSubmit={handleSubmit}>
            <label htmlFor="equation">化学方程式</label>
            <textarea
              id="equation"
              value={equation}
              onChange={(event) => setEquation(event.target.value)}
              spellCheck={false}
              rows={4}
            />
            <label htmlFor="equation-mode">表示层级</label>
            <select
              id="equation-mode"
              value={mode}
              onChange={(event) => setMode(event.target.value as EquationMode)}
            >
              {Object.entries(MODE_LABELS).map(([value, label]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
            <button className="lab-submit" type="submit" disabled={loading || !equation.trim()}>
              {loading ? '正在计算…' : '配平并验证'}
            </button>
          </form>
          <p className="lab-scope-note">
            此处只处理方程表示与守恒；不执行原子映射、键变化或机理推断。
          </p>
        </section>

        <section className="lab-panel lab-result" aria-labelledby="result-heading">
          <div className="lab-heading">
            <div><p className="eyebrow">Conservation</p><h2 id="result-heading">计算结果</h2></div>
          </div>
          {error ? <div className="lab-error" role="alert"><strong>无法配平</strong><p>{error}</p></div> : null}
          {!result && !error ? (
            <div className="lab-empty"><span>→</span><p>提交方程式后，这里显示最简系数和守恒明细。</p></div>
          ) : null}
          {result ? <EquationResult result={result} /> : null}
        </section>
      </div>
    </main>
  )
}

function EquationResult({ result }: { result: BalanceEquationResponse }) {
  const inputLabel = result.state === 'no_net_ionic'
    ? '无净离子反应'
    : result.inputState === 'balanced'
      ? '输入已经守恒'
      : '输入未配平，已求得最简整数比'
  return (
    <div className="equation-result-body">
      <span className={`lab-status state-${result.state}`}>{inputLabel}</span>
      <div className="formatted-equation" aria-label="配平结果">{result.formattedEquation}</div>
      {result.message ? <p className="lab-message">{result.message}</p> : null}
      {result.phenomenon ? <p className="lab-phenomenon"><strong>现象</strong>{result.phenomenon}</p> : null}
      {result.products.length > 0 && result.conservation.elements.length > 0 ? (
        <div className="conservation-table-wrap">
          <table>
            <caption>守恒核对</caption>
            <thead><tr><th>项目</th><th>反应物侧</th><th>生成物侧</th><th>状态</th></tr></thead>
            <tbody>
              {result.conservation.elements.map((item) => (
                <tr key={item.element}>
                  <th>{item.element}</th><td>{item.reactants}</td><td>{item.products}</td>
                  <td>{item.conserved ? '守恒' : '不守恒'}</td>
                </tr>
              ))}
              {result.conservation.charge ? (
                <tr><th>总电荷</th><td>{result.conservation.charge.reactants}</td><td>{result.conservation.charge.products}</td><td>{result.conservation.charge.conserved ? '守恒' : '不守恒'}</td></tr>
              ) : null}
            </tbody>
          </table>
        </div>
      ) : null}
      <aside className="redox-boundary">
        <strong>不从配平结果推断机理</strong>
        <p>{result.redox.message}</p>
      </aside>
    </div>
  )
}

export default function EquationLab({ onBack }: EquationLabProps) {
  return <EquationLabView onBack={onBack} onBalance={balanceEquation} />
}
