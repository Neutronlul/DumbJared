import Image from 'next/image';

export const MainIcon = ({ src="/DumbJared.png", alt = 'Icon', size = 32, className= '', ...props }) => {
  return (
    <Image
            src="/Dumbjared.png"
            width={60}
            height={60}
            alt="Screenshots of the dashboard project showing desktop version"
        {...props}
    />
  )
}
 

export const HomeIcon = ({ src="/DumbJared.png", alt = 'Icon', size = 32, className= '', ...props }) => {
  return (
    <Image
            src="/Dumbjared.png"
            width={45}
            height={45}
            className="md:block"
            alt="Screenshots of the dashboard project showing desktop version"
        {...props}
    />
  )
}
 
export const StatsIcon = ({ src="/Stats.png", alt = 'Icon', size = 32, className= '', ...props }) => {
  return (
    <Image
            src="/Stats.png"
            width={45}
            height={45}
            className="md:block"
            alt="Screenshots of the dashboard project showing desktop version"
        {...props}
    />
  )
}
 
export const ChartsIcon = ({ src="/Charts.png", alt = 'Icon', size = 32, className= '', ...props }) => {
  return (
    <Image
            src="/Charts.png"
            width={45}
            height={45}
            className="md:block"
            alt="Icon"
        {...props}
    />
  )
}
 
export const OpiniometerIcon = ({ src="/Opiniometer.png", alt = 'Icon', size = 32, className= '', ...props }) => {
  return (
    <Image
            src="/Opiniometer.png"
            width={45}
            height={45}
            className="md:block"
            alt="Screenshots of the dashboard project showing desktop version"
        {...props}
    />
  )
}
 
export const TestIcon = ({ src="/glossary.png", alt = 'Icon', size = 32, className= '', ...props }) => {
  return (
    <Image
            src="/glossary.png"
            width={45}
            height={45}
            className="md:block"
            alt="Test"
        {...props}
    />
  )
}