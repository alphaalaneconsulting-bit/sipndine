import { BrowserRouter, Routes, Route, useLocation } from "react-router-dom";
import { useEffect } from "react";
import "@/App.css";
import { AuthProvider } from "@/lib/auth";
import { Header, Footer } from "@/components/Layout";
import Home from "@/pages/Home";
import { OurStory, Menu, Buffet, Gallery, Banqueting, Catering, Offers, Membership, BookTable, Contact } from "@/pages/Pages";
import Admin from "@/pages/Admin";
import { Toaster } from "@/components/ui/sonner";

function ScrollTop() {
  const { pathname } = useLocation();
  useEffect(() => { window.scrollTo(0, 0); }, [pathname]);
  return null;
}

function PublicLayout({ children }) {
  return <><Header />{children}<Footer /></>;
}

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <AuthProvider>
          <ScrollTop />
          <Toaster position="top-center" richColors />
          <Routes>
            <Route path="/admin" element={<Admin />} />
            <Route path="*" element={<PublicLayout>
              <Routes>
                <Route path="/" element={<Home />} />
                <Route path="/our-story" element={<OurStory />} />
                <Route path="/menu" element={<Menu />} />
                <Route path="/buffet" element={<Buffet />} />
                <Route path="/gallery" element={<Gallery />} />
                <Route path="/banqueting" element={<Banqueting />} />
                <Route path="/catering" element={<Catering />} />
                <Route path="/offers" element={<Offers />} />
                <Route path="/membership" element={<Membership />} />
                <Route path="/book-table" element={<BookTable />} />
                <Route path="/contact" element={<Contact />} />
              </Routes>
            </PublicLayout>} />
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </div>
  );
}

export default App;
