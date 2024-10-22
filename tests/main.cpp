#include <iostream>
#include <z-library/backend/cpr_backend.hpp>
#include <memory>

int main()
{
    auto backend = std::make_unique<z_library::CPR_backend>();
    std::string url = "https://www.google.com";
    std::string data = backend->get_data(url);
    std::cout << data << std::endl;
    return 0;
}
