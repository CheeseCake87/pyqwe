import {render} from 'solid-js/web'

const root = document.getElementById('root')
if (import.meta.env.DEV && !(root instanceof HTMLElement)) {
    throw new Error('Root element not found. Did you forget ' +
        'to add it to your index.html? Or maybe the id attribute got misspelled?')
}

render(() => (
    <div>
        <h1>Hello PyQwe!</h1>
        <p>Welcome to the JS Example.</p>
    </div>
), root)