function Layout({ children }) {
  return (
    <main className="mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="w-full">
        {children}
      </div>
    </main>
  );
}

export default Layout;