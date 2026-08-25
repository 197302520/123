import { render, screen } from '@testing-library/vue'
import userEvent from '@testing-library/user-event'
import { describe, expect, test } from 'vitest'
import ParameterControls from './ParameterControls.vue'
import { degreeAlgorithm } from '../test/fixtures'

describe('registry parameter controls', () => {
  test('restores every edited control to defaults declared by the algorithm registry', async () => {
    const user = userEvent.setup()
    render(ParameterControls, { props: { algorithm: degreeAlgorithm, modelValue: { normalized: true, iterations: 3, mode: 'all' } } })

    const iterations = screen.getByRole('spinbutton', { name: /迭代次数/ })
    await user.clear(iterations)
    await user.type(iterations, '9')
    await user.click(screen.getByRole('checkbox', { name: /是否归一化/ }))
    await user.selectOptions(screen.getByRole('combobox', { name: /计算方式/ }), 'out')
    await user.click(screen.getByRole('button', { name: '恢复参数默认值' }))

    expect(iterations).toHaveValue(3)
    expect(screen.getByRole('checkbox', { name: /是否归一化/ })).toBeChecked()
    expect(screen.getByRole('combobox', { name: /计算方式/ })).toHaveValue('all')
  })
})
