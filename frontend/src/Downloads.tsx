import {getLanguage} from './language'
export default function Downloads(){
  if(sessionStorage.getItem('solix.launcher'))return null
  const base='https://github.com/Pacikrisko/SolarTree-AI/releases/latest/download/'
  return <footer className="solix-downloads"><strong>{getLanguage()==='en'?'Get the Solix app':'Нямаш приложението? Изтегли Solix'}</strong><a href={base+'Solix-Setup.exe'}>Windows</a><a href={base+'Solix.apk'}>Android</a></footer>
}
