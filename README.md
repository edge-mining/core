⚠️ **Disclaimer**: *This project is in a preliminary state and under active development. Features and functionality may change significantly.*

➡️ **Development Note**:
- This is the **Core repository**, which contains the main engine of the Edge Mining system.
- The [Add-on repository](https://github.com/edge-mining/addon) contains the Home Assistant integration.
- The [Docs repository](https://github.com/edge-mining/docs) specifically dedicated to documentation of the Edge Mining application.


# Edge Mining ⚡️🌞

Software to optimize the use of excess energy, especially from renewable sources, through Bitcoin mining. This system automates the turning on and off of ASIC miner devices based on energy availability, production forecasts, and user-defined policies.

## Architecture

The project uses **Hexagonal Architecture (Ports and Adapters)** to clearly separate the business logic (Domain and Application Layer) from infrastructural dependencies (Database, external APIs, Hardware Control, User Interfaces).

-   **`edge_mining/domain`**: Contains the pure business logic, subdomains and  their models (Entities, Value Objects), domain exceptions, and the interfaces (Ports) that define the contracts with the outside world.
-   **`edge_mining/application`**: Contains the application services that orchestrate the use cases, utilizing the Domain's Ports.
-   **`edge_mining/adapters`**: Contains the concrete implementations of Ports.
    -   **`domain`**: Adapters strictly used by domain elements.
    -   **`infrastructure`**: Infrastructure adapters, used cross-domain (logger, persistence, api).
-   **`edge_mining/shared`**: Shared elements (and interfaces) used cross-domain.
-   **`test`**: Contains application tests.
-   **`edge_mining/__main__.py`**: Main entry point, responsible for "wiring" dependencies (Dependency Injection).

## Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/edge-mining/core.git
    cd core
    ```
2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Linux/macOS
    # venv\Scripts\activate    # On Windows
    ```
3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Configure environment variables:**
    Copy `.env.example` to `.env` and change the values ​​according to your configuration (API keys, select the desired adapters).
    **Note:** If you use the `home_assistant_api` adapter for energy monitoring and forecast provider, make sure to configure the following correctly:
    - `HOME_ASSISTANT_URL` and `HOME_ASSISTANT_TOKEN`.
    - The `HA_ENTITY_*` IDs corresponding to your sensors in Home Assistant.
    - **Important:** The `HA_ENTITY_HOUSE_CONSUMPTION` entity should represent the house consumption *excluding* the miner load. You may need to create a `template sensor` in Home Assistant for this.
    - Check the units (`HA_UNIT_*`) and conventions (`HA_GRID_POSITIVE_EXPORT`, `HA_BATTERY_POSITIVE_CHARGE`) of your sensors.
    ```bash
    cp .env.example .env
    nano .env # Change the file .env
    ```

## Execution

You can run the application in different modes via the main entry point:

1. **Standard Mode (Default):** Starts the main automation loop that checks available energy and controls miners at regular intervals. Starts a REST API (FastAPI) server also to interact with the system programmatically.
```bash
python -m edge_mining
# Or by explicitly specifying
python -m edge_mining standard
```
2. **CLI Mode:** Access the command line interface to manage miners, policies, etc.
```bash
python -m edge_mining cli --help
python -m edge_mining cli miner list
# ...other CLI commands
```
The API will be available at `http://localhost:8001` (or the configured address and port). You can access the interactive documentation (Swagger UI) at `http://localhost:8001/docs`.

### Available adapters

- **Energy Monitor:** `dummy`, `home_assistant` (*new*)
- **Miner Controller:** `dummy`
- **Forecast Provider:** `dummy`, `home_assistant` (*new*)
- **Persistence:** `in_memory`, `sqlite` (*new*)
- **Notification:** `dummy`, `telegram` (*new*)
- **Interaction:** `cli`, `api`(*new*)

## TODO

- Implement real adapters for specific scenarios (HomeAssistant MQTT, specific ASIC APIs).
- Implement real adapters for external APIs (Solcast, OpenWeatherMap, Mining Pools).
- Add unit, integration and acceptance tests.
- Improve error handling and logging.
- Develop a web UI (could be a separate driving adapter using the API, maybe in a different repository).
- Implement more sophisticated home load forecasting logic.
- Handle authentication and authorization (especially for the API).
- Improve the rules engine.
