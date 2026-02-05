"""Custom MLServer model for Alert Recommender."""

import joblib
import numpy as np
from mlserver import MLModel
from mlserver.codecs import NumpyCodec
from mlserver.types import InferenceRequest, InferenceResponse, ResponseOutput


class AlertRecommenderModel(MLModel):
    """Custom MLServer model that loads our model components."""
    
    async def load(self) -> bool:
        """Load the model components from the joblib file."""
        model_uri = self.settings.parameters.uri
        self._components = joblib.load(model_uri)
        
        self._scaler = self._components['scaler']
        self._knn_model = self._components['knn_model']
        self._alert_labels = self._components['alert_labels']
        self._alert_types = self._components['alert_types']
        self._threshold = self._components['threshold']
        
        self.ready = True
        return self.ready
    
    async def predict(self, payload: InferenceRequest) -> InferenceResponse:
        """Make predictions using the loaded model."""
        # Decode input
        input_data = None
        for inp in payload.inputs:
            input_data = NumpyCodec.decode_input(inp)
            break
        
        if input_data is None:
            raise ValueError("No input data provided")
        
        # Scale the input
        X_scaled = self._scaler.transform(input_data)
        
        # Get nearest neighbors
        k_neighbors = min(5, len(self._alert_labels))
        distances, indices = self._knn_model.kneighbors(X_scaled, n_neighbors=k_neighbors)
        
        # Generate recommendations
        all_recommendations = []
        for idx_list in indices:
            similar_labels = self._alert_labels[idx_list]
            probabilities = similar_labels.mean(axis=0)
            
            recommendations = []
            for i, alert_type in enumerate(self._alert_types):
                if probabilities[i] >= self._threshold:
                    recommendations.append({
                        "alert_type": alert_type,
                        "probability": float(probabilities[i]),
                        "confidence": "high" if probabilities[i] >= 0.7 else "medium"
                    })
            
            all_recommendations.append(recommendations)
        
        # Encode output
        output_data = np.array(all_recommendations, dtype=object)
        
        return InferenceResponse(
            model_name=self.name,
            outputs=[
                ResponseOutput(
                    name="predictions",
                    shape=list(output_data.shape),
                    datatype="BYTES",
                    data=[str(r) for r in all_recommendations]
                )
            ]
        )
