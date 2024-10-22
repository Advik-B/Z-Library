#include <iostream>
#include <z-library/backend/cpr_backend.hpp>
#include <memory>

int main()
{
    const auto backend = std::make_unique<z_library::CPR_backend>();
    const std::string url = "https://httpbin.org/get";
    const std::string data = backend->get_data(url);
    std::cout << data << std::endl;
    return 0;
}
