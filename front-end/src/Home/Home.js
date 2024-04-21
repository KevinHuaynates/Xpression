import React from 'react';
import './Home.css';
import Header from '../Components/Header/Header';
import Hero from '../Components/Hero/Hero';
import Login from '../Components/Login/Login';
import SignUp from '../Components/SignUp/SignUp';
import ServersTable from '../Components/ServersTable/ServersTable'
import Faq from '../Components/Faq/Faq';
import Footer from '../Components/Footer/Footer';

function Home() {
    return(
        <>
            <Header/>
            <Hero/>
            <Login/>
            <SignUp/>
            <ServersTable/>
            <Faq/>
            <Footer/>
        </>
    );
}

export default Home;